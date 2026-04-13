from __future__ import annotations

"""Interview mode — follow up with personas from a previous run."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .providers import call_llm_batch, load_models_config, resolve_model

RESULTS_DIR = Path(__file__).parent.parent / "results"

INTERVIEW_SYSTEM_PROMPT = """You are participating in a content focus group follow-up interview. Stay completely in character as your assigned persona. Give specific, actionable feedback — not generic advice."""

INTERVIEW_PROMPT = """You are {name}, a {role}.
Personality: {personality}

In a previous content review, you saw this post:
---
{post_content}
---

Your original reaction: Score {score}/10 — {action}. "{reason}"

{question}

Respond naturally as this persona. Be specific and honest. 2-3 sentences max."""


def find_last_result() -> dict | None:
    """Find the most recent result file."""
    if not RESULTS_DIR.exists():
        return None

    result_dirs = sorted(RESULTS_DIR.iterdir(), reverse=True)
    for d in result_dirs:
        result_file = d / "result.json"
        if result_file.exists():
            with open(result_file) as f:
                return json.load(f)
    return None


def load_result(run_id: str) -> dict | None:
    """Load a specific run result."""
    for d in RESULTS_DIR.iterdir():
        if d.name == run_id or d.name.startswith(run_id):
            result_file = d / "result.json"
            if result_file.exists():
                with open(result_file) as f:
                    return json.load(f)
    return None


def filter_personas(
    responses: list[dict],
    filter_action: str | None = None,
    segment: str | None = None,
    post_file: str | None = None,
) -> list[dict]:
    """Filter persona responses based on criteria.

    Args:
        responses: List of persona response dicts
        filter_action: Filter by action (e.g., 'scroll_past', 'share')
        segment: Filter by segment/role
        post_file: Filter by specific post
    """
    filtered = responses

    if post_file:
        filtered = [r for r in filtered if r.get("post_file") == post_file]

    if filter_action:
        filtered = [r for r in filtered if r.get("action") == filter_action]

    if segment:
        segment_lower = segment.lower()
        filtered = [r for r in filtered if segment_lower in r.get("segment", "").lower()]

    return filtered


async def run_interview(
    result: dict,
    question: str | None = None,
    filter_action: str | None = None,
    segment: str | None = None,
    post_file: str | None = None,
    model_override: str | None = None,
    preset: str | None = None,
    provider_override: str | None = None,
) -> dict:
    """Run follow-up interviews with personas from a previous run.

    Args:
        result: Previous run result dict
        question: Custom question to ask (default: "What would make you engage with this?")
        filter_action: Filter personas by action
        segment: Filter personas by segment
        model_override: Explicit model
        preset: Model preset

    Returns:
        Interview result dict
    """
    responses = result["results"]["persona_responses"]

    # Use explicit --post if given, otherwise default to winner for battle mode
    target_file = post_file
    if not target_file and result["mode"] == "battle" and result["results"].get("winner"):
        target_file = result["results"]["winner"]["post_file"]

    filtered = filter_personas(
        responses,
        filter_action=filter_action,
        segment=segment,
        post_file=target_file,
    )

    if not filtered:
        return {"error": "No personas match the filter criteria.", "filter": filter_action, "segment": segment}

    # Check guardrails
    config = load_models_config()
    guardrails = config.get("guardrails", {})
    max_interviews = guardrails.get("max_interviews_per_run", 50)
    if len(filtered) > max_interviews:
        filtered = filtered[:max_interviews]

    # Default question based on filter
    if not question:
        if filter_action == "scroll_past":
            question = "What would make you stop and read this post? Be specific."
        elif filter_action == "share":
            question = "What specifically made you want to reshare this? What about it resonated?"
        elif filter_action == "save":
            question = "What made this worth saving? How would you use this later?"
        else:
            question = "What would make you engage more with this post? Be specific."

    model, temperature = resolve_model("interview", model_override, preset)

    # Reconstruct post content from result
    # In a real run, the post would be saved alongside the result
    post_content = "[Post from previous run]"

    all_prompts = []
    for persona_resp in filtered:
        prompt = INTERVIEW_PROMPT.format(
            name=persona_resp["persona"],
            role=persona_resp["segment"],
            personality=f"Based on {persona_resp['segment']} profile",
            post_content=post_content,
            score=persona_resp.get("score", "?"),
            action=persona_resp.get("action", "?"),
            reason=persona_resp.get("reason", "No reason given"),
            question=question,
        )
        all_prompts.append({
            "prompt": prompt,
            "system_prompt": INTERVIEW_SYSTEM_PROMPT,
        })

    responses_text = await call_llm_batch(
        prompts=all_prompts,
        model=model,
        temperature=temperature,
        max_tokens=300,
        max_concurrent=config.get("max_concurrent", 20),
        provider_override=provider_override,
    )

    interview_responses = []
    for i, text in enumerate(responses_text):
        interview_responses.append({
            "persona": filtered[i]["persona"],
            "segment": filtered[i]["segment"],
            "original_score": filtered[i].get("score"),
            "original_action": filtered[i].get("action"),
            "response": text,
        })

    return {
        "id": f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-interview",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "interview",
        "source_run": result.get("id"),
        "question": question,
        "filter": filter_action,
        "segment": segment,
        "personas_interviewed": len(interview_responses),
        "model": model,
        "responses": interview_responses,
    }
