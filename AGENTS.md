# AI Vibe Check — Cursor / Copilot / Windsurf Context

## Project Summary

Python CLI tool: AI focus group for content creators. Simulated personas score posts before publishing.

## Stack

- Python 3.10+ (3.12 recommended), pip-installable via setup.py
- LiteLLM for all LLM providers (OpenRouter, OpenAI, Anthropic, Ollama, Groq, Gemini, DeepSeek)
- python-dotenv for .env loading
- argparse CLI, asyncio for concurrent LLM calls
- JSON config files (no database)

## Key Files

| File | Purpose |
|------|---------|
| `vibe_check/cli.py` | CLI entry point, dotenv loading, argument parsing |
| `vibe_check/init.py` | `vibe-check init` — guided onboarding + dynamic persona generation |
| `vibe_check/simulate.py` | Core simulation engine, brutal prompt, weighted scoring |
| `vibe_check/interview.py` | Follow-up interview mode (--post, --filter, --segment, --ask) |
| `vibe_check/personas.py` | Persona generation (deterministic + LLM modes) |
| `vibe_check/report.py` | Output formatting (triple score: Content/Engagement/Final) |
| `vibe_check/providers.py` | Auto-detect provider from env keys + LiteLLM routing |
| `config/audiences/*.json` | Audience definitions + platform-specific scoring_weights |
| `config/models.json` | Model presets (free/cheap/quality/local) + guardrails |
| `docs/cost-guide.md` | Full cost matrix (4 models × 4 agent tiers) |

## Model Defaults

All commands default to `openai/gpt-4o-mini`. For interview mode, offer the user a choice before running — gpt-4o gives deeper responses but costs more. Use `--model openai/gpt-4o` or `--preset quality` to upgrade.

## Conventions

- All LLM calls go through `providers.py` (never call litellm directly)
- Provider auto-detected from env keys: OPENROUTER → OPENAI → ANTHROPIC → GROQ → GEMINI → DEEPSEEK
- Model strings stay clean in config (e.g., `openai/gpt-4o-mini`) — routing adds prefix at call time
- Persona responses must be JSON: `{score, action, reason, improvement}`
- Scoring: Final = 40% content + 60% engagement (weighted by platform-specific action weights)
- Results auto-save to `results/` as JSON
- Config is the source of truth — no hardcoded model names or limits
- Guardrails enforced in code: max agents, max cost, token limits

## Setup

```bash
pip install -e .
vibe-check init   # Guided setup: answers 5 questions, validates API key, generates custom audience
```

No JSON editing required. `vibe-check init` handles API key setup and persona generation.

## Testing

```bash
vibe-check battle --dry-run --platform linkedin posts/  # Cost estimate only (no API key needed)
vibe-check generate-personas --platform linkedin         # Deterministic, no API calls
```
