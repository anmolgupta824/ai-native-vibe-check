# Personas

## How It Works

Each audience config defines **segments** (e.g., "Senior Engineer × 25"). The persona generator creates unique individuals within each segment with varied personalities, experience levels, and quirks.

## Two Generation Modes

### 1. Deterministic (Default, Free)
```bash
vibe-check generate-personas --platform linkedin
```
Fast, no API calls. Creates varied personas using hashed randomization.

### 2. LLM-Generated (Richer, Costs API Calls)
```bash
vibe-check generate-personas --platform linkedin --llm
```
Uses LLM to create unique personalities, hot takes, and communication styles. More realistic but costs ~80 API calls.

## Storage

Generated personas are cached in `personas/generated/` (gitignored).
Regenerate anytime — they'll be overwritten.

## Auto-Generation

If you run `vibe-check battle` without generating personas first, deterministic personas are auto-created and cached.
