# 🎯 AI Vibe Check

> AI focus group for content creators. 80 simulated personas score your posts before you publish.

**The problem:** You write 3 LinkedIn drafts. You pick one based on gut. It flops. The one you killed would've gone viral.

**The fix:** Run your drafts through 80 simulated personas. Get a winner in 2 minutes. Post with confidence.

## How It Works

```
You write 3 drafts
  ↓
vibe-check battle --platform linkedin drafts/
  ↓
80 personas score all 3 (Engineers, PMs, CTOs, Founders, DevRel...)
  ↓
Post 2 wins (82/100). Here's why. Here's what to fix.
```

**Requirements:** Python 3.10+ (3.12 recommended) | One API key (OpenRouter, OpenAI, or any LLM provider)

If this saves you from posting a flop, consider giving it a ⭐

## Quick Start

```bash
git clone https://github.com/anmolgupta824/ai-vibe-check.git
cd ai-vibe-check
pip install -e .
vibe-check init
```

`vibe-check init` walks you through 5 questions, validates your API key, and generates a custom audience tailored to your platform and content type. Takes ~2 minutes. No JSON editing.

Then run your first battle:

```bash
vibe-check battle --platform linkedin examples/posts/
```

**AI-first (optional):** Open the repo in Claude Code and say: *"Vibe check these 3 drafts for LinkedIn"*

## Try it now (no setup)

No API key needed to see how it works:

```bash
# See how it works without an API key
vibe-check battle --dry-run examples/posts/linkedin-sample.txt examples/posts/threads-sample.txt
```

## Cost

80 agents scoring 3 posts = 240 API calls.

| Model | Per battle | Monthly (20 battles) | Time |
|-------|-----------|---------------------|------|
| Free (Qwen 72B) | $0 | $0 | ~12 min |
| GPT-4o-mini | $0.05 | $1.00 | ~1.5 min |
| Claude Haiku | $0.08 | $1.60 | ~1.5 min |

→ Full breakdown: [docs/cost-guide.md](docs/cost-guide.md)

## Three Modes

### 1. Battle — Which post wins?

```bash
vibe-check battle --platform linkedin draft1.txt draft2.txt draft3.txt
```

```
⚔️  VIBE CHECK — BATTLE MODE
Platform: LinkedIn | Audience: Tech LinkedIn (80 personas)
──────────────────────────────────────────────────

🏆 WINNER: draft2.txt

📊 Rankings:
  1. draft2.txt ████████████████████░  82/100  ← SHIP THIS
  2. draft1.txt ██████████████░░░░░░░  71/100
  3. draft3.txt ████████████░░░░░░░░░  64/100

💬 Top Reactions:
  DevRel #5: "I'd reshare. The 90→25 numbers are specific enough to be credible."
  CTO #3: "First AI tool post with an actual cost number. Refreshing."
```

### 2. Hooks — Which opening line wins?

```bash
vibe-check hooks --platform linkedin --post winner.txt \
  --hook "I built a digest agent for $0.006/run" \
  --hook "90 articles in, 25 out. My AI curator never sleeps" \
  --hook "Stop reading newsletters. Build one that reads for you"
```

### 3. Interview — Why did people scroll past?

```bash
# Ask the scrollers what would make them stop
vibe-check interview --last --filter scroll_past

# Ask CTOs a specific question
vibe-check interview --last --segment "CTO" --ask "Would you share this?"
```

## Supported Platforms

| Platform | Default Audience | Config |
|----------|-----------------|--------|
| LinkedIn | Tech audience (80 personas) | `config/audiences/linkedin-tech.json` |
| Threads | Broad AI audience (80 personas) | `config/audiences/threads-broad-ai.json` |
| Custom | Your audience | Run `vibe-check init` or edit manually |

## Supported LLM Providers

Uses [LiteLLM](https://github.com/BerriAI/litellm) — one dependency handles everything.

| Provider | Model | Cost per battle |
|----------|-------|----------------|
| OpenRouter (free tier) | Qwen 2.5 72B | $0 |
| OpenAI | GPT-4o-mini | ~$0.01 |
| Anthropic | Claude Haiku | ~$0.02 |
| Ollama (local) | Qwen 32B | $0 |
| Groq (free) | Llama 3.3 70B | $0 |

```bash
# Use presets
vibe-check battle --preset free --platform linkedin posts/      # Free models
vibe-check battle --preset quality --platform linkedin posts/   # Best models
vibe-check battle --preset local --platform linkedin posts/     # Ollama

# Or specify directly
vibe-check battle --model "ollama/qwen2.5:32b" --platform linkedin posts/
```

## Create Your Own Audience

The easiest way:

```bash
vibe-check init   # Generates custom-{platform}.json automatically
```

Or regenerate with a different count:

```bash
vibe-check regenerate --audience audiences/custom-linkedin.json --count 100
```

Manual editing is still supported — see `config/audiences/README.md` for the schema.

## Track Accuracy

After posting, log your actual results:

```bash
vibe-check log-outcome --posted draft2.txt --impressions 7200 --likes 89 --saves 49
```

After 10+ logged outcomes:

```bash
vibe-check stats
```

## All Commands

```bash
vibe-check init                           # First-time setup (guided)
vibe-check regenerate --audience X        # Regenerate audience with new settings
vibe-check battle [posts...]              # Compare 2-5 drafts
vibe-check hooks --post X --hook A --hook B  # Test opening lines
vibe-check score [post]                   # Score single post
vibe-check interview --last               # Follow up with personas
vibe-check generate-personas              # Regenerate persona pool
vibe-check log-outcome                    # Log real performance
vibe-check stats                          # Accuracy dashboard
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--platform` | `linkedin` or `threads` (default: linkedin) |
| `--audience` | Path to custom audience JSON |
| `--model` | Override LLM model |
| `--preset` | `free`, `cheap`, `quality`, or `local` |
| `--agents` | Override persona count (20=quick, 80=default, 500=deep) |
| `--dry-run` | Estimate cost without running |

## AI-First Setup

This repo includes context files for AI coding assistants:
- `CLAUDE.md` — Claude Code
- `AGENTS.md` — Cursor / Copilot / Windsurf
- `GEMINI.md` — Gemini

Open the repo in your AI editor and say: *"Vibe check these 3 drafts for LinkedIn"*

## License

MIT
