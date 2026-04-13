from __future__ import annotations

"""vibe-check init — guided onboarding + dynamic persona generation."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv, set_key

load_dotenv()

AUDIENCES_DIR = Path(__file__).parent.parent / "audiences"
REF_AUDIENCES_DIR = Path(__file__).parent.parent / "config" / "audiences"

PROVIDER_INFO = [
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/keys", True),
    ("openai", "OPENAI_API_KEY", "https://platform.openai.com/api-keys", False),
    ("anthropic", "ANTHROPIC_API_KEY", "https://console.anthropic.com/keys", False),
    ("groq", "GROQ_API_KEY", "https://console.groq.com/keys", True),
]

# Content type keywords → pre-built audience file
PRESETS = {
    "linkedin-tech.json": ["ai", "developer", "tools", "engineering", "agent", "code", "devtools", "software"],
    "threads-broad-ai.json": ["threads", "viral", "general", "broad", "meme", "casual"],
}

PERSONA_GENERATION_PROMPT = """You are designing an AI focus group for a content creator.

Platform: {platform}
Content type: {content_type}
Audience description: {audience_description}
Total personas needed: {total_count}
Additional preferences: {additional_prefs}

Generate a complete audience configuration JSON for this creator.

Requirements:
- Create 10-20 distinct segments (not generic buckets — be specific)
- Each segment should react differently to content
- scroll_past_triggers must be concrete and specific (not "bad content")
- engagement_style must describe exact behavior (what they click, what they share)
- Counts must sum exactly to {total_count}
- Platform rules must reflect how {platform} actually works
- scoring_weights: LinkedIn rewards comments+shares (5pts each), Threads rewards reposts+likes

Output ONLY valid JSON matching this schema exactly:
{{
  "name": "Custom {platform_title} Audience — {content_type_short}",
  "platform": "{platform}",
  "generated_by": "vibe-check init",
  "generated_at": "{generated_at}",
  "description": "{audience_description}",
  "total_personas": {total_count},
  "segments": [
    {{
      "role": "Role Name",
      "count": 12,
      "traits": ["trait1", "trait2", "trait3"],
      "engagement_style": "Specific behavior description — what they click, share, or comment on.",
      "scroll_past_triggers": ["no demo shown", "vague claims", "buzzword soup"],
      "interests": ["topic1", "topic2", "topic3"]
    }}
  ],
  "platform_rules": {{
    "max_post_length": 3000,
    "tone": "professional but direct",
    "what_works": ["working demos", "specific numbers"],
    "what_fails": ["hype without proof", "no hook"]
  }},
  "scoring_weights": {{
    "comment": 5,
    "share": 5,
    "save": 2,
    "click": 2,
    "like": 1
  }}
}}

Be realistic and harsh. Most personas scroll past most content.
The default action is always scroll past. Engagement is earned, not assumed.
"""


def _hr():
    print("\n" + "━" * 40 + "\n")


def _check_existing_key() -> tuple[str | None, str | None]:
    """Return (provider, env_var) if a key is already set, else (None, None)."""
    from .providers import PROVIDER_KEYS
    for env_var, provider in PROVIDER_KEYS:
        key = os.environ.get(env_var, "")
        if key and not key.startswith("sk-or-...") and key not in ("", "sk-...", "sk-ant-..."):
            return provider, env_var
    return None, None


def _detect_preset(content_type: str) -> str | None:
    """Return preset filename if content type matches known keywords, else None."""
    lower = content_type.lower()
    for filename, keywords in PRESETS.items():
        if any(kw in lower for kw in keywords):
            return filename
    return None


def _prompt_platform() -> str:
    print("📱 Which platform are you posting on?")
    print("  1. LinkedIn")
    print("  2. Threads")
    print("  3. Both")
    while True:
        choice = input("\n> ").strip()
        if choice == "1":
            return "linkedin"
        elif choice == "2":
            return "threads"
        elif choice == "3":
            return "both"
        else:
            print("  Enter 1, 2, or 3.")


def _prompt_content_type() -> str:
    print("✍️  What type of content do you usually post?")
    print("   (examples: AI tools, product management, startup stories, dev tutorials, finance)\n")
    while True:
        val = input("> ").strip()
        if val:
            return val
        print("  Please enter a content type.")


def _prompt_audience_description() -> str:
    print("👥 Describe your target audience in 1-2 sentences.")
    print("   Who are you trying to reach? What do they care about?\n")
    while True:
        val = input("> ").strip()
        if val:
            return val
        print("  Please describe your audience.")


def _prompt_persona_count() -> int:
    print("🔢 How many personas?")
    print("  1. 20  — Quick gut check (~15 sec)")
    print("  2. 50  — Standard focus group (~45 sec)")
    print("  3. 100 — Deep analysis (~90 sec)")
    while True:
        choice = input("\n> ").strip()
        if choice == "1":
            return 20
        elif choice == "2":
            return 50
        elif choice == "3":
            return 100
        else:
            print("  Enter 1, 2, or 3.")


def _prompt_additional_prefs() -> str:
    print("🎯 Any specific types of people you want MORE of in your audience? (optional)")
    print('   Example: "More startup founders", "More PMs", "Include investors"')
    print("   Press Enter to skip.\n")
    val = input("> ").strip()
    return val


def _prompt_provider_and_key() -> tuple[str, str, str]:
    """Ask user for provider, show link, get key. Returns (provider, env_var, key)."""
    print("🔑  Almost done. Which AI provider do you have a key for?\n")
    print("  1. OpenRouter  ← Recommended (one key, all models, free tier available)")
    print("  2. OpenAI      (GPT-4o-mini)")
    print("  3. Anthropic   (Claude Haiku)")
    print("  4. Groq        (Llama 3 — free)\n")

    while True:
        choice = input("> ").strip()
        if choice in ("1", "2", "3", "4"):
            break
        print("  Enter 1, 2, 3, or 4.")

    provider, env_var, url, _ = PROVIDER_INFO[int(choice) - 1]
    print(f"\n📋 Get your free {provider.title()} key (30 seconds):")
    print(f"   → {url}\n")

    while True:
        key = input("Paste your key: ").strip()
        if key:
            return provider, env_var, key
        print("  Key cannot be empty.")


def _validate_key(provider: str, env_var: str, key: str) -> bool:
    """Make a cheap 1-token test call. Returns True if valid."""
    import litellm
    litellm.suppress_debug_info = True

    # Set temporarily for validation
    os.environ[env_var] = key

    from .providers import detect_provider, route_model
    from .providers import PROVIDER_BASE_URLS

    # Pick cheapest/fastest model per provider for validation
    test_models = {
        "openrouter": "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-4-5-20251001",
        "groq": "groq/llama-3.3-70b-versatile",
        "gemini": "gemini/gemini-1.5-flash",
        "deepseek": "deepseek/deepseek-chat",
    }
    model_str = test_models.get(provider, "openai/gpt-4o-mini")
    routed = route_model(model_str, provider)
    base_url = PROVIDER_BASE_URLS.get(provider)

    kwargs = {
        "model": routed,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 3,
        "temperature": 0,
    }
    if base_url:
        kwargs["api_base"] = base_url
    if key:
        kwargs["api_key"] = key

    try:
        import asyncio
        asyncio.run(litellm.acompletion(**kwargs))
        return True
    except Exception:
        return False


def _save_key_to_env(env_var: str, key: str):
    """Write key to .env file and set in current process."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        example = Path(__file__).parent.parent / ".env.example"
        if example.exists():
            env_path.write_text(example.read_text())
        else:
            env_path.write_text("")
    set_key(str(env_path), env_var, key)
    os.environ[env_var] = key


def _check_existing_audience(platform: str) -> Path | None:
    """Return path if custom audience already exists for this platform."""
    path = AUDIENCES_DIR / f"custom-{platform}.json"
    return path if path.exists() else None


def _handle_existing_audience(path: Path) -> str | None:
    """Ask user what to do with existing file. Returns new filename or None to skip generation."""
    print(f"⚠️  {path.name} already exists.")
    print("  1. Overwrite (regenerate with new questions)")
    print("  2. Keep existing (use as-is)")
    print("  3. Save as new file (enter name)")
    while True:
        choice = input("> ").strip()
        if choice == "1":
            return path.name
        elif choice == "2":
            return None  # signal: skip generation
        elif choice == "3":
            name = input("Filename (without .json): ").strip()
            return f"{name}.json" if name else path.name
        else:
            print("  Enter 1, 2, or 3.")


async def _generate_audience(
    platform: str,
    content_type: str,
    audience_description: str,
    total_count: int,
    additional_prefs: str,
    output_filename: str,
) -> Path:
    """Call LLM to generate audience JSON and save it."""
    from .providers import call_llm, resolve_model

    model, temperature = resolve_model("persona_generation")

    prompt = PERSONA_GENERATION_PROMPT.format(
        platform=platform,
        content_type=content_type,
        audience_description=audience_description,
        total_count=total_count,
        additional_prefs=additional_prefs or "None",
        platform_title=platform.title(),
        content_type_short=content_type[:30],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    print(f"\n🧠 Generating {total_count} custom personas for your audience...")

    response = await call_llm(
        prompt=prompt,
        model=model,
        temperature=0.8,
        max_tokens=4000,
    )

    # Parse JSON — strip markdown fences if present
    raw = response.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    audience = json.loads(raw)

    AUDIENCES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AUDIENCES_DIR / output_filename
    with open(out_path, "w") as f:
        json.dump(audience, f, indent=2)

    return out_path


def _print_audience_preview(audience: dict):
    """Print segment summary preview."""
    segments = audience.get("segments", [])
    total = audience.get("total_personas", "?")
    print(f"\n✅ Audience created: audiences/{audience.get('name', 'custom')}")
    print(f"   {total} personas across {len(segments)} segments\n")
    print("Preview:")
    for seg in segments[:5]:
        traits_preview = seg.get("traits", [])
        traits_str = ", ".join(traits_preview[:2]) if traits_preview else ""
        print(f"  - {seg['role']} ({seg['count']}) — {traits_str}")
    if len(segments) > 5:
        print(f"  - ... {len(segments) - 5} more segments")


def run_init():
    """Main entry point for `vibe-check init`."""
    print("\n🎯 Welcome to Vibe Check — AI Focus Group for Content Creators")
    print("Scores text posts only (LinkedIn, Threads). No images or video.")
    print("Let's build your audience in 2 minutes.")
    _hr()

    # Step 1: Check for existing API key
    existing_provider, existing_env_var = _check_existing_key()
    if existing_provider:
        print(f"✅ Found {existing_provider.title()} key. Skipping key setup.")

    # Step 2: Audience questions (always asked first)
    platform = _prompt_platform()
    _hr()

    content_type = _prompt_content_type()
    _hr()

    # Preset detection
    if platform != "both":
        preset_file = _detect_preset(content_type)
        if preset_file:
            print(f"💡 We have a pre-built audience for this:")
            print(f'   "{preset_file.replace(".json", "").replace("-", " ").title()}" (validated against 20+ real posts)\n')
            print("  1. Use pre-built audience (faster, validated)")
            print("  2. Generate custom audience (tailored to your exact description)")
            choice = input("\n> ").strip()
            if choice == "1":
                preset_path = REF_AUDIENCES_DIR / preset_file
                print(f"\n✅ Using reference audience: config/audiences/{preset_file}")
                print(f"\n🚀 Ready. Run your first battle:")
                print(f"   vibe-check battle --platform {platform} posts/")
                return
            _hr()

    audience_description = _prompt_audience_description()
    _hr()

    total_count = _prompt_persona_count()
    _hr()

    additional_prefs = _prompt_additional_prefs()
    _hr()

    # Step 3: API key (if not already set)
    if not existing_provider:
        provider, env_var, key = _prompt_provider_and_key()
        print("\n✅ Key received. Testing connection...", end=" ", flush=True)
        if _validate_key(provider, env_var, key):
            print("Connected ✓")
            _save_key_to_env(env_var, key)
        else:
            print("\n❌ Key validation failed. Common issues:")
            print(f"   - Copy the full key including the prefix")
            print(f"   - Make sure there are no spaces")
            if provider == "openrouter":
                print(f"   - OpenRouter free tier: confirm email first at openrouter.ai")
            while True:
                retry = input("\nTry again? [Y/n]: ").strip().lower()
                if retry in ("n", "no"):
                    print("Exiting. Run `vibe-check init` again when you have a valid key.")
                    sys.exit(1)
                # Re-prompt for key
                key = input("Paste your key: ").strip()
                print("Testing...", end=" ", flush=True)
                if _validate_key(provider, env_var, key):
                    print("Connected ✓")
                    _save_key_to_env(env_var, key)
                    break
                else:
                    print("❌ Still failing.")
        _hr()

    # Step 4: Handle existing audience file
    platforms_to_generate = ["linkedin", "threads"] if platform == "both" else [platform]
    output_filenames = {}

    for p in platforms_to_generate:
        existing = _check_existing_audience(p)
        if existing:
            result = _handle_existing_audience(existing)
            if result is None:
                # User chose to keep existing
                print(f"\n✅ Using existing audiences/custom-{p}.json")
                print(f"\n🚀 Ready. Run your first battle:")
                print(f"   vibe-check battle --platform {p} posts/")
                return
            output_filenames[p] = result
        else:
            output_filenames[p] = f"custom-{p}.json"

    # Step 5: Generate audience(s)
    count_per_platform = total_count if len(platforms_to_generate) == 1 else total_count // 2

    for p in platforms_to_generate:
        try:
            out_path = asyncio.run(_generate_audience(
                platform=p,
                content_type=content_type,
                audience_description=audience_description,
                total_count=count_per_platform,
                additional_prefs=additional_prefs,
                output_filename=output_filenames[p],
            ))
            with open(out_path) as f:
                audience = json.load(f)
            _print_audience_preview(audience)
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse LLM response as JSON: {e}")
            print("   Try running `vibe-check init` again.")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Generation failed: {e}")
            sys.exit(1)

    # Step 6: Done
    primary_platform = platforms_to_generate[0]
    print(f"\n🚀 Ready. Run your first battle:")
    print(f"   vibe-check battle --platform {primary_platform} posts/")
    print(f"\nYour custom audience is auto-detected. No --audience flag needed.")


def run_regenerate(audience_path: str | None, count: int | None, fresh: bool):
    """Entry point for `vibe-check regenerate`."""
    if fresh:
        run_init()
        return

    if not audience_path:
        print("❌ Specify --audience or use --fresh to start over.")
        sys.exit(1)

    path = Path(audience_path)
    if not path.exists():
        for base in (AUDIENCES_DIR, REF_AUDIENCES_DIR):
            alt = base / audience_path
            if alt.exists():
                path = alt
                break
        else:
            print(f"❌ Audience file not found: {audience_path}")
            sys.exit(1)

    with open(path) as f:
        existing = json.load(f)

    platform = existing.get("platform", "linkedin")
    description = existing.get("description") or existing.get("name", "")
    content_type = description
    audience_description = description
    total_count = count or existing.get("total_personas", 50)

    print(f"\n🔄 Regenerating {path.name} with {total_count} personas...")

    try:
        out_path = asyncio.run(_generate_audience(
            platform=platform,
            content_type=content_type,
            audience_description=audience_description,
            total_count=total_count,
            additional_prefs="",
            output_filename=path.name,
        ))
        with open(out_path) as f:
            audience = json.load(f)
        _print_audience_preview(audience)
        print(f"\n✅ Regenerated: {path}")
    except Exception as e:
        print(f"\n❌ Regeneration failed: {e}")
        sys.exit(1)
