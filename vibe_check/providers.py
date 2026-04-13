from __future__ import annotations

"""LLM provider abstraction via LiteLLM."""

import asyncio
import json
import os
from pathlib import Path

import litellm

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True

CONFIG_PATH = Path(__file__).parent.parent / "config" / "models.json"


def load_models_config() -> dict:
    """Load models.json config."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def resolve_model(task: str, model_override: str | None = None, preset: str | None = None) -> tuple[str, float]:
    """Resolve which model to use for a given task.

    Args:
        task: One of 'simulate', 'interview', 'persona_generation'
        model_override: Explicit --model flag from CLI
        preset: Preset name from --preset flag

    Returns:
        (model_string, temperature)
    """
    config = load_models_config()

    if model_override:
        temp = config["models"].get(task, {}).get("temperature", 0.7)
        return model_override, temp

    if preset and preset in config.get("presets", {}):
        model = config["presets"][preset][task]
        temp = config["models"].get(task, {}).get("temperature", 0.7)
        return model, temp

    model_config = config["models"][task]
    return model_config["model"], model_config["temperature"]


# Provider detection order: first key found wins
PROVIDER_KEYS = [
    ("OPENROUTER_API_KEY", "openrouter"),
    ("OPENAI_API_KEY", "openai"),
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("GROQ_API_KEY", "groq"),
    ("GEMINI_API_KEY", "gemini"),
    ("DEEPSEEK_API_KEY", "deepseek"),
]

PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
}


class NoAPIKeyError(SystemExit):
    """Raised when no API key is found in environment."""
    pass


def detect_provider(provider_override: str | None = None) -> tuple[str, str, str | None]:
    """Auto-detect provider from environment variables.

    Args:
        provider_override: Explicit --provider flag or "provider" in models.json.
                          Skips auto-detection, looks for that provider's key directly.

    Returns:
        (provider_name, api_key, base_url_or_None)
    """
    # Check models.json for explicit provider setting
    if not provider_override:
        config = load_models_config()
        provider_override = config.get("provider")

    # If explicit provider, look for that specific key
    if provider_override:
        for env_var, provider in PROVIDER_KEYS:
            if provider == provider_override:
                key = os.environ.get(env_var)
                if key and not key.startswith("sk-or-...") and key not in ("", "sk-..."):
                    base_url = PROVIDER_BASE_URLS.get(provider)
                    return provider, key, base_url
                print(f"❌ Provider '{provider_override}' selected but {env_var} not set.")
                print(f"   Set it in .env: {env_var}=your-key-here")
                raise NoAPIKeyError(1)

    # Auto-detect: first key found wins
    for env_var, provider in PROVIDER_KEYS:
        key = os.environ.get(env_var)
        if key and not key.startswith("sk-or-...") and key not in ("", "sk-..."):
            base_url = PROVIDER_BASE_URLS.get(provider)
            return provider, key, base_url

    # No key found
    print("❌ No API key found. Set one in .env:")
    print("")
    print("   OPENROUTER_API_KEY=sk-or-...   (recommended — one key, all models)")
    print("   OPENAI_API_KEY=sk-...          (OpenAI direct)")
    print("   ANTHROPIC_API_KEY=sk-ant-...   (Anthropic direct)")
    print("   GROQ_API_KEY=gsk_...           (Groq — free tier)")
    print("")
    print("   Get a free OpenRouter key: https://openrouter.ai/keys")
    print("   Then: cp .env.example .env && edit .env")
    raise NoAPIKeyError(1)


def route_model(model: str, provider: str) -> str:
    """Add provider prefix to model string if needed.

    Model strings in config are clean (e.g., 'openai/gpt-4o-mini').
    LiteLLM needs provider-specific routing:
      - OpenRouter: 'openrouter/openai/gpt-4o-mini'
      - OpenAI direct: 'gpt-4o-mini' (strip 'openai/' prefix)
      - Anthropic direct: 'claude-sonnet-4' (strip 'anthropic/' prefix)
      - Groq: 'groq/llama-3.3-70b' (already has prefix)
      - Ollama: pass through as-is
    """
    # Already has the right prefix (local, free tier models)
    if model.startswith("ollama/") or model.startswith("groq/"):
        return model

    if provider == "openrouter":
        # OpenRouter needs openrouter/ prefix
        if not model.startswith("openrouter/"):
            return f"openrouter/{model}"
        return model

    if provider == "openai":
        # Direct OpenAI — strip 'openai/' prefix, LiteLLM handles it
        if model.startswith("openai/"):
            return model[len("openai/"):]
        return model

    if provider == "anthropic":
        # Direct Anthropic — strip 'anthropic/' prefix
        if model.startswith("anthropic/"):
            return model[len("anthropic/"):]
        return model

    if provider == "groq":
        # Groq — add groq/ prefix if not present
        if not model.startswith("groq/"):
            # Strip provider prefix if present (e.g., 'openai/gpt-4o-mini' won't work on Groq)
            return f"groq/{model.split('/')[-1]}"
        return model

    if provider == "gemini":
        if model.startswith("gemini/"):
            return model
        return f"gemini/{model.split('/')[-1]}"

    if provider == "deepseek":
        if model.startswith("deepseek/"):
            return model
        return f"deepseek/{model.split('/')[-1]}"

    # Fallback: pass through
    return model


async def call_llm(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 200,
    system_prompt: str | None = None,
    provider_override: str | None = None,
) -> str:
    """Make a single LLM call via LiteLLM.

    Auto-detects provider from env vars and routes the model string accordingly.
    Model strings stay clean in config (e.g., 'openai/gpt-4o-mini').
    """
    provider, api_key, base_url = detect_provider(provider_override)
    routed_model = route_model(model, provider)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": routed_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if base_url:
        kwargs["api_base"] = base_url
    if api_key:
        kwargs["api_key"] = api_key

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content


async def call_llm_batch(
    prompts: list[dict],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 200,
    max_concurrent: int = 20,
    provider_override: str | None = None,
) -> list[str]:
    """Run multiple LLM calls concurrently with rate limiting.

    Args:
        prompts: List of dicts with 'prompt' and optional 'system_prompt'
        model: Model string
        temperature: Sampling temperature
        max_tokens: Max output tokens per call
        max_concurrent: Max concurrent requests
        provider_override: Explicit provider from --provider flag

    Returns:
        List of response texts (same order as prompts)
    """
    config = load_models_config()
    max_concurrent_cfg = config.get("max_concurrent", 20)
    semaphore = asyncio.Semaphore(min(max_concurrent, max_concurrent_cfg))

    async def _call(p: dict) -> str:
        async with semaphore:
            try:
                return await call_llm(
                    prompt=p["prompt"],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system_prompt=p.get("system_prompt"),
                    provider_override=provider_override,
                )
            except Exception as e:
                return f"[ERROR] {e}"

    tasks = [_call(p) for p in prompts]
    return await asyncio.gather(*tasks)
