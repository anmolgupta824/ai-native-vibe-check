# Audience Configs

Each JSON file defines a focus group for a specific platform.

## Structure

```json
{
  "name": "Audience Name",
  "platform": "linkedin|threads|twitter|youtube|reddit",
  "total_personas": 80,
  "segments": [
    {
      "role": "Segment Name",
      "count": 25,
      "traits": ["trait1", "trait2"],
      "engagement_style": "How they interact with content",
      "scroll_past_triggers": ["what makes them ignore posts"],
      "interests": ["topic1", "topic2"]
    }
  ],
  "platform_rules": {
    "max_post_length": 3000,
    "tone": "platform tone",
    "what_works": ["patterns that perform well"],
    "what_fails": ["patterns that flop"]
  }
}
```

## Reference vs User-Generated Audiences

| Directory | Purpose | Git |
|-----------|---------|-----|
| `config/audiences/` | Pre-built reference audiences (defaults) | ✅ Tracked |
| `audiences/` | Your custom audiences from `vibe-check init` | ❌ Gitignored |

## Creating Your Own

**Recommended:** Run `vibe-check init` — answers 5 questions, generates a custom audience tailored to your platform and content type. Saved to `audiences/custom-{platform}.json`.

**Manual:** Copy a reference file as a template:
```bash
cp config/audiences/linkedin-tech.json audiences/my-audience.json
# Edit segments, traits, platform rules
vibe-check battle --audience audiences/my-audience.json posts/
```

## Auto-Detection

When you run any battle/score/hooks command without `--audience`, the lookup order is:

1. `audiences/custom-{platform}.json` (your generated audience)
2. `config/audiences/{platform}-tech.json` (reference default)

After `vibe-check init`, no `--audience` flag needed.
