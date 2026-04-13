from __future__ import annotations

"""Core simulation engine — load personas, run LLM calls, aggregate results."""

import asyncio
import json
import re
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path

from .personas import generate_personas_sync, load_personas, save_personas
from .providers import call_llm_batch, load_models_config, resolve_model

SIMULATE_SYSTEM_PROMPT = """You are participating in a content focus group simulation. You must respond ONLY as your assigned persona — stay in character completely.

Respond in this exact JSON format (no markdown, no code fences):
{
  "score": <1-10>,
  "action": "<like|comment|share|save|scroll_past|click_link>",
  "reason": "<one sentence explaining your reaction as this persona>",
  "improvement": "<one specific thing that would increase your score by 2 points>"
}"""

SIMULATE_USER_PROMPT = """You are {name}, a {role} with {years_experience} years of experience.

Personality: {personality}
Interests: {interests}
Engagement style: {engagement_style}
What makes you scroll past: {scroll_past_triggers}

You're scrolling {platform}. You see 200 posts a day. You engage with maybe 5. The rest you scroll past in under 2 seconds. You are brutally selective with your attention.

Here's a post:

---
{post_content}
---

Be brutally honest. Most posts are forgettable. Default is scroll past.

1. Score (1-10):
   1-2 = garbage, instant scroll
   3-4 = generic, nothing new, scroll past
   5 = average, might glance but won't stop
   6 = decent, would pause but probably not engage
   7 = good, would stop and read fully
   8 = strong, would engage (like/comment/save)
   9 = exceptional, would share with my network
   10 = once-a-month post, would reshare AND comment

2. Action: Pick exactly ONE — the strongest action you'd take:
   scroll_past / like / comment / save / share / click_link
   (Most posts = scroll_past. Be honest.)

3. Why: One sentence. Be specific, not generic.

4. Improvement: One specific change that would move your score up by 2 points."""

HOOKS_USER_PROMPT = """You are {name}, a {role} with {years_experience} years of experience.

Personality: {personality}
Engagement style: {engagement_style}
What makes you scroll past: {scroll_past_triggers}
Interests: {interests}

You're scrolling {platform} and see a post that starts with this hook:

---
{hook}
---

The full post follows:
---
{post_content}
---

Rate ONLY the hook (opening line). Does it make you stop scrolling and read the full post?
Respond as this persona. Be honest and specific. Score 1-10."""


def _parse_response(text: str) -> dict:
    """Parse a persona's JSON response, handling common LLM output issues."""
    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from mixed output
        match = re.search(r'\{[^{}]*"score"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Last resort: extract score from text
        score_match = re.search(r'"?score"?\s*[:=]\s*(\d+)', text)
        action_match = re.search(r'"?action"?\s*[:=]\s*"?(\w+)"?', text)
        return {
            "score": int(score_match.group(1)) if score_match else 5,
            "action": action_match.group(1) if action_match else "scroll_past",
            "reason": text[:200],
            "improvement": "N/A (parse error)",
            "_parse_error": True,
        }


async def simulate_battle(
    posts: list[dict],
    audience_path: Path,
    model_override: str | None = None,
    preset: str | None = None,
    agents: int | None = None,
    dry_run: bool = False,
    provider_override: str | None = None,
) -> dict:
    """Run battle mode — multiple posts scored by all personas.

    Args:
        posts: List of dicts with 'file' and 'content' keys
        audience_path: Path to audience JSON config
        model_override: Explicit model override
        preset: Model preset name
        agents: Override persona count
        dry_run: Just estimate cost, don't run

    Returns:
        Full result dict with rankings, responses, metadata
    """
    with open(audience_path) as f:
        audience = json.load(f)

    platform = audience["platform"]

    # Load or generate personas
    personas = load_personas(audience_path)
    if not personas:
        personas = generate_personas_sync(audience)
        save_personas(audience["name"], personas)

    # Override agent count if specified
    if agents and agents < len(personas):
        # Proportionally sample from each segment
        personas = personas[:agents]
    elif agents and agents > len(personas):
        personas = personas[:len(personas)]  # Can't exceed generated count

    model, temperature = resolve_model("simulate", model_override, preset)
    config = load_models_config()
    max_concurrent = config.get("max_concurrent", 20)

    total_calls = len(personas) * len(posts)
    estimated_tokens = total_calls * 350  # ~150 input + 200 output per call

    if dry_run:
        return {
            "dry_run": True,
            "agents": len(personas),
            "posts": len(posts),
            "api_calls": total_calls,
            "estimated_tokens": estimated_tokens,
            "model": model,
        }

    # Check guardrails
    guardrails = config.get("guardrails", {})
    max_agents = guardrails.get("max_agents_per_run", 1000)
    max_posts = guardrails.get("max_posts_per_battle", 5)

    if len(personas) > max_agents:
        raise ValueError(f"Agent limit exceeded. Max: {max_agents}")
    if len(posts) > max_posts:
        raise ValueError(f"Post limit exceeded. Max: {max_posts}")

    # Build prompts for all persona × post combinations
    all_prompts = []
    prompt_map = []  # Track which persona/post each prompt belongs to

    for post in posts:
        for persona in personas:
            prompt = SIMULATE_USER_PROMPT.format(
                name=persona["name"],
                role=persona["role"],
                years_experience=persona.get("years_experience", "several"),
                personality=persona.get("personality", "Professional"),
                engagement_style=persona.get("engagement_style", "Standard"),
                scroll_past_triggers=", ".join(persona.get("scroll_past_triggers", [])),
                interests=", ".join(persona.get("interests", [])),
                platform=platform,
                post_content=post["content"],
            )
            all_prompts.append({
                "prompt": prompt,
                "system_prompt": SIMULATE_SYSTEM_PROMPT,
            })
            prompt_map.append({
                "persona": persona["name"],
                "segment": persona["role"],
                "post_file": post["file"],
            })

    # Run all LLM calls
    responses = await call_llm_batch(
        prompts=all_prompts,
        model=model,
        temperature=temperature,
        max_tokens=200,
        max_concurrent=max_concurrent,
        provider_override=provider_override,
    )

    # Parse responses and build results
    persona_responses = []
    for i, raw_response in enumerate(responses):
        parsed = _parse_response(raw_response)
        persona_responses.append({
            **prompt_map[i],
            **parsed,
        })

    # Load platform-specific scoring weights
    default_weights = {"comment": 5, "share": 5, "save": 2, "click": 2, "like": 1}
    scoring_weights = audience.get("scoring_weights", default_weights)

    # Aggregate scores per post
    post_scores = {}
    for post in posts:
        post_responses = [r for r in persona_responses if r["post_file"] == post["file"]]
        scores = [r["score"] for r in post_responses if isinstance(r.get("score"), (int, float))]
        actions = [r["action"] for r in post_responses]

        comment_count = sum(1 for a in actions if a == "comment")
        share_count = sum(1 for a in actions if a == "share")
        save_count = sum(1 for a in actions if a == "save")
        click_count = sum(1 for a in actions if a == "click_link")
        like_count = sum(1 for a in actions if a == "like")
        scroll_past_count = sum(1 for a in actions if a == "scroll_past")
        total = len(scores)

        # Content score: raw average of what personas rated (0-100)
        avg_score = sum(scores) / total if total else 0
        content_score = round(avg_score * 10, 1)

        # Engagement score: weighted by actions (0-100)
        if total > 0:
            weighted_raw = (
                (comment_count * scoring_weights.get("comment", 5)) +
                (share_count * scoring_weights.get("share", 5)) +
                (save_count * scoring_weights.get("save", 2)) +
                (click_count * scoring_weights.get("click", 2)) +
                (like_count * scoring_weights.get("like", 1))
            ) / total
            engagement_score = round(min(weighted_raw * 10, 100), 1)
        else:
            engagement_score = 0

        # Final score: 40% content + 60% engagement
        final_score = round((content_score * 0.4) + (engagement_score * 0.6), 1)

        post_scores[post["file"]] = {
            "post_file": post["file"],
            "score": round(avg_score, 1),
            "content_score": content_score,
            "engagement_score": engagement_score,
            "final_score": final_score,
            "score_normalized": final_score,  # Used for ranking
            "engagement_count": total - scroll_past_count,
            "share_count": share_count,
            "save_count": save_count,
            "comment_count": comment_count,
            "scroll_past_count": scroll_past_count,
            "click_count": click_count,
            "like_count": like_count,
            "total_personas": total,
        }

    # Rank posts by final score (40% content + 60% engagement)
    rankings = sorted(post_scores.values(), key=lambda x: x["final_score"], reverse=True)
    winner = rankings[0] if rankings else None

    # Unique run ID: date + platform + mode + short hash of posts+audience
    id_seed = "|".join(p["file"] for p in posts) + "|" + audience["name"]
    id_hash = md5(id_seed.encode()).hexdigest()[:6]

    result = {
        "id": f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{platform}-battle-{id_hash}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "mode": "battle",
        "audience": audience["name"],
        "audience_file": str(audience_path),
        "model": model,
        "posts_tested": len(posts),
        "personas_used": len(personas),
        "total_api_calls": total_calls,
        "results": {
            "winner": winner,
            "rankings": rankings,
            "persona_responses": persona_responses,
        },
        "outcome": None,
    }

    return result


async def simulate_hooks(
    post: dict,
    hooks: list[str],
    audience_path: Path,
    model_override: str | None = None,
    preset: str | None = None,
    agents: int | None = None,
    dry_run: bool = False,
    provider_override: str | None = None,
) -> dict:
    """Run hooks mode — test different opening lines for a post.

    Args:
        post: Dict with 'file' and 'content' keys
        hooks: List of hook strings to test
        audience_path: Path to audience JSON config
        model_override: Explicit model override
        preset: Model preset name
        agents: Override persona count
        dry_run: Just estimate cost, don't run

    Returns:
        Full result dict with hook rankings
    """
    with open(audience_path) as f:
        audience = json.load(f)

    platform = audience["platform"]

    personas = load_personas(audience_path)
    if not personas:
        personas = generate_personas_sync(audience)
        save_personas(audience["name"], personas)

    if agents and agents < len(personas):
        personas = personas[:agents]

    model, temperature = resolve_model("simulate", model_override, preset)
    config = load_models_config()
    max_concurrent = config.get("max_concurrent", 20)

    total_calls = len(personas) * len(hooks)

    if dry_run:
        return {
            "dry_run": True,
            "agents": len(personas),
            "hooks": len(hooks),
            "api_calls": total_calls,
            "model": model,
        }

    # Check guardrails
    guardrails = config.get("guardrails", {})
    if len(hooks) > guardrails.get("max_hooks_per_test", 5):
        raise ValueError(f"Hook limit exceeded. Max: {guardrails['max_hooks_per_test']}")

    all_prompts = []
    prompt_map = []

    for hi, hook in enumerate(hooks):
        for persona in personas:
            prompt = HOOKS_USER_PROMPT.format(
                name=persona["name"],
                role=persona["role"],
                years_experience=persona.get("years_experience", "several"),
                personality=persona.get("personality", "Professional"),
                engagement_style=persona.get("engagement_style", "Standard"),
                scroll_past_triggers=", ".join(persona.get("scroll_past_triggers", [])),
                interests=", ".join(persona.get("interests", [])),
                platform=platform,
                hook=hook,
                post_content=post["content"],
            )
            all_prompts.append({
                "prompt": prompt,
                "system_prompt": SIMULATE_SYSTEM_PROMPT,
            })
            prompt_map.append({
                "persona": persona["name"],
                "segment": persona["role"],
                "hook_index": hi,
                "hook": hook[:80],
            })

    responses = await call_llm_batch(
        prompts=all_prompts,
        model=model,
        temperature=temperature,
        max_tokens=200,
        max_concurrent=max_concurrent,
        provider_override=provider_override,
    )

    persona_responses = []
    for i, raw_response in enumerate(responses):
        parsed = _parse_response(raw_response)
        persona_responses.append({
            **prompt_map[i],
            **parsed,
        })

    # Aggregate per hook
    hook_scores = {}
    for hi, hook in enumerate(hooks):
        hook_responses = [r for r in persona_responses if r["hook_index"] == hi]
        scores = [r["score"] for r in hook_responses if isinstance(r.get("score"), (int, float))]
        avg_score = sum(scores) / len(scores) if scores else 0
        actions = [r["action"] for r in hook_responses]

        hook_scores[hi] = {
            "hook_index": hi,
            "hook": hook,
            "score": round(avg_score, 1),
            "score_normalized": round(avg_score * 10, 0),
            "would_stop": sum(1 for a in actions if a != "scroll_past"),
            "would_scroll": sum(1 for a in actions if a == "scroll_past"),
            "total_personas": len(scores),
        }

    rankings = sorted(hook_scores.values(), key=lambda x: x["score"], reverse=True)

    id_seed = post["file"] + "|" + "|".join(hooks[:3]) + "|" + audience["name"]
    id_hash = md5(id_seed.encode()).hexdigest()[:6]

    return {
        "id": f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{platform}-hooks-{id_hash}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "mode": "hooks",
        "audience": audience["name"],
        "model": model,
        "hooks_tested": len(hooks),
        "personas_used": len(personas),
        "results": {
            "winner": rankings[0] if rankings else None,
            "rankings": rankings,
            "persona_responses": persona_responses,
        },
        "outcome": None,
    }


async def simulate_score(
    post: dict,
    audience_path: Path,
    model_override: str | None = None,
    preset: str | None = None,
    agents: int | None = None,
    dry_run: bool = False,
    provider_override: str | None = None,
) -> dict:
    """Score a single post — simplified battle with one post."""
    result = await simulate_battle(
        posts=[post],
        audience_path=audience_path,
        model_override=model_override,
        preset=preset,
        agents=agents,
        dry_run=dry_run,
        provider_override=provider_override,
    )
    if not result.get("dry_run"):
        result["mode"] = "score"
        result["id"] = result["id"].replace("-battle", "-score")
    return result
