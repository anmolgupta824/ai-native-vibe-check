<p align="center">
  <h1 align="center">AI-Native Vibe Check</h1>
  <p align="center">
    AI focus group for content creators. Simulate how your audience reacts to your post — before you publish. Get a winner in 2 minutes.
  </p>
</p>

<p align="center">
  <a href="https://github.com/anmolgupta824/ai-native-vibe-check/stargazers"><img src="https://img.shields.io/github/stars/anmolgupta824/ai-native-vibe-check?style=for-the-badge&color=yellow" alt="Stars"></a>
  <a href="https://github.com/anmolgupta824/ai-native-vibe-check/network/members"><img src="https://img.shields.io/github/forks/anmolgupta824/ai-native-vibe-check?style=for-the-badge" alt="Forks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/anmolgupta824/ai-native-vibe-check/issues"><img src="https://img.shields.io/github/issues/anmolgupta824/ai-native-vibe-check?style=for-the-badge" alt="Issues"></a>
</p>

<p align="center">
  <b>Your audience. Simulated. Brutally honest.</b>
  <br/>
  <i>Works with OpenRouter, OpenAI, Anthropic, Groq, Gemini — bring your own key</i>
  <br/><br/>
  <a href="https://github.com/anmolgupta824/ai-native-vibe-check/stargazers"><img src="https://img.shields.io/badge/Like%20this%3F-Give%20it%20a%20%E2%AD%90-yellow?style=for-the-badge" alt="Star this repo"></a>
</p>

---

## The problem

You write 3 LinkedIn drafts. You pick one based on gut. It flops. The one you killed would've gone viral.

**The fix:** Run your drafts through simulated personas. Get a winner in 2 minutes. Post with confidence.

```
You write 3 drafts
  ↓
vibe-check battle --platform linkedin drafts/
  ↓
80 personas score all 3 (Engineers, PMs, CTOs, Founders, DevRel...)
  ↓
Post 2 wins (82/100). Here's why. Here's what to fix.
```

**Requirements:** Python 3.10+ (3.12 recommended) | One API key (free tier available)

---

## Onboarding — Build Your Audience First

Before running any battle, you need an audience. Run `vibe-check init` once. It takes 2 minutes.

```bash
$ vibe-check init

🎯 Welcome to Vibe Check — AI Focus Group for Content Creators
Let's build your audience in 2 minutes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Which platform are you posting on?
  1. LinkedIn
  2. Threads
  3. Both
> 1

✍️  What type of content do you usually post?
> AI tools and agents for developers

👥 Describe your target audience in 1-2 sentences.
> Senior engineers, CTOs, and indie hackers who build with AI.
  Skeptical of hype, value working demos, share content that saves them time.

🔢 How many personas?
  1. 20  — Quick gut check (~15 sec)
  2. 50  — Standard focus group (~45 sec)
  3. 100 — Deep analysis (~90 sec)
> 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔑  Almost done. Which AI provider do you have a key for?
  1. OpenRouter  ← Recommended (free tier available)
  2. OpenAI
  3. Anthropic
  4. Groq (free)
> 1

✅ Key saved. Testing connection... Connected ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 Generating 50 custom personas for your audience...

✅ 50 personas across 12 segments

Preview:
  - Senior Engineer (12) — skeptical, values depth, shares proven tools
  - Indie Hacker (8) — action-oriented, clones repos immediately
  - CTO / VP Eng (6) — high signal bar, rarely comments, reshares selectively
  - AI Researcher (5) — technical, follows papers, corrects wrong claims
  - DevRel / Advocate (5) — amplifier, quote-posts with commentary
  - ... 7 more segments

🚀 Ready. Run your first battle:
   vibe-check battle --platform linkedin posts/
```

Your custom audience is saved to `audiences/` (gitignored — never committed). After init, no `--audience` flag needed.

---

## Quick Start

```bash
git clone https://github.com/anmolgupta824/ai-native-vibe-check.git
cd ai-native-vibe-check
pip install -e .
vibe-check init
```

Then run your first battle:

```bash
vibe-check battle --platform linkedin examples/posts/linkedin-sample.txt examples/posts/threads-sample.txt
```

**AI-first (optional):** Open in Claude Code, Cursor, or Windsurf and say: *"Vibe check these 3 drafts for LinkedIn"*

---

## Try it now (no API key needed)

```bash
vibe-check battle --dry-run examples/posts/linkedin-sample.txt examples/posts/threads-sample.txt
```

---

## Three Modes

### 1. Battle — Which post wins?

```bash
vibe-check battle --platform linkedin draft1.txt draft2.txt draft3.txt
```

```
⚔️  VIBE CHECK — BATTLE MODE
Platform: LinkedIn | Audience: Custom LinkedIn — AI/Dev (50 personas)
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
  --hook "I built a digest agent for \$0.006/run" \
  --hook "90 articles in, 25 out. My AI curator never sleeps" \
  --hook "Stop reading newsletters. Build one that reads for you"
```

### 3. Interview — Why did they scroll past?

```bash
vibe-check interview --last --filter scroll_past
vibe-check interview --last --segment "CTO" --ask "Would you share this?"
```

---

## Cost

80 agents scoring 3 posts = 240 API calls.

| Model | Per battle | Monthly (20 battles) | Time |
|-------|-----------|---------------------|------|
| Free (Qwen 72B via OpenRouter) | $0 | $0 | ~12 min |
| GPT-4o-mini | ~$0.05 | ~$1.00 | ~1.5 min |
| Claude Haiku | ~$0.08 | ~$1.60 | ~1.5 min |

→ Full breakdown: [docs/cost-guide.md](docs/cost-guide.md)

---

## Supported Providers

Uses [LiteLLM](https://github.com/BerriAI/litellm) — one dependency, any model.

| Provider | Free Tier | Get Key |
|----------|-----------|---------|
| OpenRouter | ✅ Yes | https://openrouter.ai/keys |
| OpenAI | ❌ | https://platform.openai.com/api-keys |
| Anthropic | ❌ | https://console.anthropic.com/keys |
| Groq | ✅ Yes | https://console.groq.com/keys |
| Gemini | ✅ Yes | https://aistudio.google.com/apikey |

```bash
vibe-check battle --preset free posts/     # Free models only
vibe-check battle --preset quality posts/  # Best models
vibe-check battle --preset local posts/    # Ollama (fully local)
```

---

## All Commands

| Command | What it does |
|---------|-------------|
| `vibe-check init` | First-time setup — build your custom audience |
| `vibe-check regenerate` | Regenerate audience with new settings |
| `vibe-check battle` | Compare 2-5 post drafts, pick a winner |
| `vibe-check score` | Score a single post |
| `vibe-check hooks` | Test hook variants for the same post |
| `vibe-check interview` | Ask personas why they scrolled, shared, or saved |
| `vibe-check log-outcome` | Log real impressions/likes after posting |
| `vibe-check stats` | Accuracy report — swarm vs reality |

---

## Common Flags

| Flag | Description |
|------|-------------|
| `--platform` | `linkedin` or `threads` (default: linkedin) |
| `--audience` | Override audience path |
| `--agents` | Override persona count (20=quick, 80=default) |
| `--preset` | `free`, `cheap`, `quality`, or `local` |
| `--dry-run` | Estimate cost, no API key needed |
| `--no-share` | Skip share card prompt |

---

## AI-First Setup

This repo includes context files for every major AI coding tool:

| File | For |
|------|-----|
| `CLAUDE.md` | Claude Code |
| `AGENTS.md` | Cursor, Copilot, Windsurf |
| `GEMINI.md` | Gemini CLI |

Open the repo in your AI editor and say: *"Vibe check these 3 drafts for LinkedIn"*

---

## License

MIT
