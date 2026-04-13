# AI Vibe Check — Claude Code Context

## What This Is

AI focus group for content creators. 80 simulated personas score your posts before you publish.

**Three modes:**
- `battle` — Compare 2-5 post drafts → get a winner
- `hooks` — Test hook variants → pick the best opening line
- `interview` — Follow up with personas → understand WHY

## First-Run Setup (Do This Before Any vibe-check Command)

When a user opens this repo with Claude Code for the first time, run through this setup automatically:

1. **Check Python version:** Run `python3 --version`. If below 3.10, tell the user: "Python 3.10+ required (you have X.Y). Install via `brew install python@3.12` or `conda create -n vibe-check python=3.12`." Stop and wait for them to fix it.

2. **Install:** Run `pip install -e .`

3. **Verify:** Run `vibe-check --version` to confirm installation.

4. **Set up your audience:** Run `vibe-check init`
   - Answer 5 questions about your platform and audience
   - API key setup included — asked last, validated before saving to `.env`
   - 50 custom personas generated automatically via LLM
   - Takes ~2 minutes, one-time setup

**Only after setup is confirmed should you run any vibe-check commands.**

## Architecture

```
config/audiences/*.json  → Who the personas are (segments, traits, platform rules, scoring_weights)
config/models.json       → Which LLM to use + presets (free/cheap/quality/local) + guardrails
vibe_check/              → Python package (pip-installable)
  cli.py                 → CLI entry point (argparse, dotenv loading)
  simulate.py            → Core engine (persona × post LLM calls + weighted aggregation)
  interview.py           → Follow-up questions to personas from previous runs
  personas.py            → Generate individual personas from segments
  report.py              → Format output (terminal with triple score display)
  providers.py           → Auto-detect provider from env keys + LiteLLM routing
results/                 → Auto-saved per run (gitignored)
personas/generated/      → Cached generated personas (gitignored)
docs/cost-guide.md       → Full cost matrix (4 models × 4 agent tiers)
```

## Key Design Decisions

- **Auto-detect provider** — user sets ONE API key in `.env`, code figures out routing. Priority: OpenRouter → OpenAI → Anthropic → Groq → Gemini → DeepSeek.
- **LiteLLM** handles all providers — one dependency, any model
- **Config-driven** — swap audience JSON, get different focus group. No code changes.
- **Clean model strings** — config says `openai/gpt-4o-mini`, routing adds provider prefix at call time
- **Deterministic personas by default** — fast, no API calls. Use `--llm` for richer generation.
- **All results saved as JSON** — no database needed
- **Guardrails in config/models.json** — max agents, max cost, token limits
- **Weighted scoring** — Final = 40% content score + 60% engagement score. Platform-specific weights.
- **Brutal prompt** — "200 posts/day, engage with 5. Default is scroll past." Score anchoring prevents inflated scores.

## Model Defaults

All commands default to `openai/gpt-4o-mini` (cheap, fast). Before running interview mode, ask the user:

> "Interview defaults to gpt-4o-mini. Want deeper responses? Options:
> - `--model openai/gpt-4o` — more nuanced ($0.15 vs $0.01 per interview)
> - `--preset quality` — upgrades interview to gpt-4o automatically
> - Default (gpt-4o-mini) — fine for most cases"

Only ask once per session. If user picks quality, use `--preset quality` for subsequent interviews.

## Scoring System

Three scores per post:
- **Content Score** (0-100): Raw average of persona ratings × 10
- **Engagement Score** (0-100): Weighted by actions (comment/share × 5, save/click × 2, like × 1 for LinkedIn)
- **Final Score** (0-100): 40% content + 60% engagement

Platform weights are in `config/audiences/*.json` under `scoring_weights`. LinkedIn rewards comments+shares. Threads rewards likes+reposts.

## How to Help Users

When a user pastes drafts and asks for feedback:

1. Save each draft to a temp file
2. Run: `vibe-check battle --platform linkedin draft1.txt draft2.txt draft3.txt`
3. Show the formatted results (triple score: Content / Engagement / Final)
4. If they want to dig deeper: `vibe-check interview --last --filter scroll_past`
5. To interview about a specific post: `vibe-check interview --last --post draft2.txt --filter scroll_past`

When a user wants to test hooks:

1. Save the winning post to a file
2. Run: `vibe-check hooks --platform linkedin --post winner.txt --hook "Hook A" --hook "Hook B"`

## Environment

- Needs one API key set in `.env` (auto-loaded via python-dotenv)
- Auto-detects provider from which key is set — no config needed
- Override with `--provider openai` flag or `"provider": "openai"` in models.json
- Free tier available: `--preset free`
- Local mode: `--preset local` (requires Ollama)
- Dry-run works without any API key: `--dry-run`

## Commands Reference

```bash
# Battle — compare posts
vibe-check battle --platform linkedin posts/draft1.txt posts/draft2.txt
vibe-check battle --platform threads --preset free posts/

# Hooks — test opening lines
vibe-check hooks --platform linkedin --post winner.txt --hook "Hook A" --hook "Hook B"

# Score — single post feedback
vibe-check score --platform linkedin post.txt

# Interview — follow up with personas
vibe-check interview --last --filter scroll_past                    # Scrollers from winning post
vibe-check interview --last --post draft2.txt --filter scroll_past  # Scrollers from specific post
vibe-check interview --last --segment "CTO" --ask "Would you share this?"
vibe-check interview --last --filter share --ask "What made you reshare?"

# Personas
vibe-check generate-personas --platform linkedin         # Deterministic (free)
vibe-check generate-personas --platform linkedin --llm   # LLM-generated (richer)

# Track accuracy
vibe-check log-outcome --posted draft2.txt --impressions 7200
vibe-check stats

# Cost estimate (no API key needed)
vibe-check battle --dry-run --platform linkedin posts/
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--platform` | `linkedin` or `threads` (default: linkedin) |
| `--audience` | Path to custom audience JSON |
| `--model` | Override model (e.g., `openai/gpt-4o-mini`) |
| `--preset` | `free`, `cheap`, `quality`, or `local` |
| `--provider` | Force provider: `openrouter`, `openai`, `anthropic`, `groq`, `gemini`, `deepseek` |
| `--agents` | Override persona count (20=quick, 80=default, 500=deep) |
| `--dry-run` | Estimate cost without running (no API key needed) |
| `--post` | (interview) Which post to interview about |
| `--filter` | (interview) Filter by action: `scroll_past`, `share`, `save`, etc. |
| `--segment` | (interview) Filter by role: `CTO`, `Senior Engineer`, etc. |
| `--ask` | (interview) Custom question to ask personas |
