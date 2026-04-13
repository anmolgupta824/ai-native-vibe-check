from __future__ import annotations

"""Persona generation from audience config segments."""

import json
import random
from pathlib import Path

from .providers import call_llm, resolve_model

PERSONAS_DIR = Path(__file__).parent.parent / "personas" / "generated"

GENERATION_PROMPT = """You are creating a unique persona for an AI focus group simulation.

Segment: {role}
Traits: {traits}
Engagement style: {engagement_style}
Scroll-past triggers: {scroll_past_triggers}
Interests: {interests}

Generate persona #{number} of {total} for this segment. Make them UNIQUE — different personality, years of experience, communication quirks, hot takes.

Respond in this exact JSON format (no markdown, no code fences):
{{
  "name": "{role} #{number}",
  "role": "{role}",
  "years_experience": <number>,
  "personality": "<2-3 sentence unique personality description>",
  "communication_style": "<how they write comments/reactions>",
  "hot_take": "<one strong opinion they hold>",
  "engagement_style": "<specific way they engage with content>",
  "scroll_past_triggers": {scroll_past_triggers_json},
  "interests": {interests_json}
}}"""


def get_personas_path(audience_name: str) -> Path:
    """Get the path for generated personas file."""
    safe_name = audience_name.lower().replace(" ", "-").replace("/", "-")
    return PERSONAS_DIR / f"{safe_name}.json"


def load_personas(audience_path: Path) -> list[dict]:
    """Load generated personas for an audience. Returns empty list if not generated yet."""
    with open(audience_path) as f:
        audience = json.load(f)

    personas_path = get_personas_path(audience["name"])
    if personas_path.exists():
        with open(personas_path) as f:
            return json.load(f)
    return []


def generate_personas_sync(audience: dict) -> list[dict]:
    """Generate simple personas without LLM calls (deterministic, fast).

    Creates varied personas from segment definitions using randomization.
    Use generate_personas_llm() for richer, LLM-generated personas.
    """
    personas = []
    experience_ranges = {
        "Senior Engineer": (8, 20),
        "Product Manager": (3, 15),
        "CTO / VP Engineering": (12, 25),
        "DevRel / Content Creator": (3, 12),
        "Founder / Indie Hacker": (2, 15),
        "Junior Developer": (0, 3),
        "Recruiter": (2, 10),
        "Casual Tech Enthusiast": (0, 5),
        "AI Curious Non-Tech": (0, 3),
        "Junior Dev / Student": (0, 2),
        "Content Creator / Meme Account": (1, 8),
        "Journalist / Writer": (3, 15),
        "Skeptic / Troll": (0, 10),
        "Indie Hacker": (2, 10),
    }

    personality_modifiers = [
        "harsh critic", "enthusiastic supporter", "quiet observer",
        "cynical veteran", "eager learner", "devil's advocate",
        "practical pragmatist", "visionary dreamer", "data-driven analyst",
        "storytelling enthusiast", "no-nonsense minimalist", "empathetic connector",
        "contrarian thinker", "detail-oriented perfectionist", "big-picture strategist",
        "humor-driven communicator", "skeptical evaluator", "collaborative builder",
        "trend-chasing early adopter", "methodical researcher",
    ]

    for segment in audience["segments"]:
        role = segment["role"]
        count = segment["count"]
        exp_range = experience_ranges.get(role, (1, 10))

        for i in range(1, count + 1):
            modifier = personality_modifiers[(hash(f"{role}{i}") + i) % len(personality_modifiers)]
            years = exp_range[0] + (hash(f"{role}{i}exp") % (exp_range[1] - exp_range[0] + 1))

            persona = {
                "name": f"{role} #{i}",
                "role": role,
                "years_experience": years,
                "personality": f"{modifier.title()}. {years} years experience. {', '.join(segment['traits'][:2])}.",
                "communication_style": segment["engagement_style"],
                "engagement_style": segment["engagement_style"],
                "scroll_past_triggers": segment["scroll_past_triggers"],
                "interests": segment["interests"],
                "segment_index": i,
            }
            personas.append(persona)

    return personas


async def generate_personas_llm(
    audience: dict,
    model_override: str | None = None,
    preset: str | None = None,
) -> list[dict]:
    """Generate rich personas using LLM calls.

    Each segment generates N unique personas with varied personalities.
    Results are cached to personas/generated/.
    """
    model, temperature = resolve_model("persona_generation", model_override, preset)
    personas = []

    for segment in audience["segments"]:
        role = segment["role"]
        count = segment["count"]

        for i in range(1, count + 1):
            prompt = GENERATION_PROMPT.format(
                role=role,
                traits=", ".join(segment["traits"]),
                engagement_style=segment["engagement_style"],
                scroll_past_triggers=", ".join(segment["scroll_past_triggers"]),
                interests=", ".join(segment["interests"]),
                number=i,
                total=count,
                scroll_past_triggers_json=json.dumps(segment["scroll_past_triggers"]),
                interests_json=json.dumps(segment["interests"]),
            )

            try:
                response = await call_llm(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=300,
                )
                # Parse JSON response
                persona = json.loads(response.strip())
                personas.append(persona)
            except (json.JSONDecodeError, Exception) as e:
                # Fallback to deterministic persona on failure
                personas.append({
                    "name": f"{role} #{i}",
                    "role": role,
                    "years_experience": random.randint(2, 15),
                    "personality": f"Generated fallback. {', '.join(segment['traits'][:2])}.",
                    "communication_style": segment["engagement_style"],
                    "engagement_style": segment["engagement_style"],
                    "scroll_past_triggers": segment["scroll_past_triggers"],
                    "interests": segment["interests"],
                    "error": str(e),
                })

    return personas


async def generate_from_description(
    platform: str,
    content_type: str,
    audience_description: str,
    total_count: int,
    additional_prefs: str = "",
    output_filename: str | None = None,
) -> Path:
    """Generate a custom audience JSON from a user description via LLM.

    Wraps the init.py generation logic for use by other modules.
    Returns the path to the saved audience file.
    """
    from .init import _generate_audience, AUDIENCES_DIR

    filename = output_filename or f"custom-{platform}.json"
    return await _generate_audience(
        platform=platform,
        content_type=content_type,
        audience_description=audience_description,
        total_count=total_count,
        additional_prefs=additional_prefs,
        output_filename=filename,
    )


def save_personas(audience_name: str, personas: list[dict]) -> Path:
    """Save generated personas to disk."""
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    path = get_personas_path(audience_name)
    with open(path, "w") as f:
        json.dump(personas, f, indent=2)
    return path
