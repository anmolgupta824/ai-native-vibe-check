# AI Vibe Check — Gemini Context

## What This Is

Python CLI: AI focus group for content creators. 80 simulated personas score posts before publishing.

## Setup

```bash
pip install -e .
vibe-check init   # Guided setup: 5 questions, validates API key, generates custom audience
```

Requires Python 3.10+ (3.12 recommended). No JSON editing required.

## Architecture

- `vibe_check/` — Python package: CLI, simulation engine, interview mode, provider auto-detection
- `config/audiences/*.json` — Audience definitions with platform-specific scoring weights
- `config/models.json` — Model presets (free/cheap/quality/local) + guardrails
- `results/` — Auto-saved run results (gitignored)
- `docs/cost-guide.md` — Full cost matrix

## Provider Auto-Detection

Set ONE API key in `.env`. Code auto-detects which provider to use:
1. OPENROUTER_API_KEY → routes through OpenRouter (recommended)
2. OPENAI_API_KEY → OpenAI direct
3. ANTHROPIC_API_KEY → Anthropic direct
4. GROQ_API_KEY → Groq direct
5. GEMINI_API_KEY → Gemini direct

Override with `--provider` flag on any command.

## Model Defaults

All commands default to `openai/gpt-4o-mini`. For interviews, ask the user if they want deeper responses — `--model openai/gpt-4o` or `--preset quality` upgrades interview quality at higher cost.

## Scoring

Three scores per post:
- Content Score (0-100): raw persona ratings
- Engagement Score (0-100): weighted by actions (platform-specific weights)
- Final Score (0-100): 40% content + 60% engagement

## Commands

```bash
vibe-check init                                           # First-time setup (guided)
vibe-check regenerate --audience config/audiences/custom-linkedin.json --count 100
vibe-check battle --platform linkedin posts/              # Compare 2-5 posts
vibe-check hooks --post x.txt --hook "A" --hook "B"       # Test opening lines
vibe-check score --platform linkedin post.txt             # Score single post
vibe-check interview --last --filter scroll_past          # Interview scrollers
vibe-check interview --last --post x.txt --filter share   # Interview about specific post
vibe-check generate-personas --platform linkedin          # Create persona pool
vibe-check stats                                          # Accuracy report
vibe-check battle --dry-run posts/                        # Cost estimate (no key needed)
```
