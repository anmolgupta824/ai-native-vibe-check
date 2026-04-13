# Cost Guide

80 agents scoring 3 posts = 240 API calls. Here's what that costs across models and agent tiers.

## Cost Matrix

### 80 Agents (Default)

| Model | Per Battle | Time | Monthly (20 battles) |
|-------|-----------|------|---------------------|
| Free (Qwen 72B) | $0 | ~12 min | $0 |
| GPT-4o-mini | $0.05 | ~1.5 min | $1.00 |
| Claude Haiku | $0.08 | ~1.5 min | $1.60 |
| GPT-4o | $0.80 | ~3 min | $16.00 |

### 100 Agents

| Model | Per Battle | Time | Monthly (20 battles) |
|-------|-----------|------|---------------------|
| Free (Qwen 72B) | $0 | ~15 min | $0 |
| GPT-4o-mini | $0.06 | ~2 min | $1.20 |
| Claude Haiku | $0.10 | ~2 min | $2.00 |
| GPT-4o | $1.00 | ~4 min | $20.00 |

### 500 Agents (Deep Analysis)

| Model | Per Battle | Time | Monthly (20 battles) |
|-------|-----------|------|---------------------|
| Free (Qwen 72B) | $0 | ~75 min | $0 |
| GPT-4o-mini | $0.30 | ~8 min | $6.00 |
| Claude Haiku | $0.50 | ~8 min | $10.00 |
| GPT-4o | $5.00 | ~15 min | $100.00 |

### 1000 Agents (Maximum)

| Model | Per Battle | Time | Monthly (20 battles) |
|-------|-----------|------|---------------------|
| Free (Qwen 72B) | $0 | ~150 min | $0 |
| GPT-4o-mini | $0.60 | ~15 min | $12.00 |
| Claude Haiku | $1.00 | ~15 min | $20.00 |
| GPT-4o | $10.00 | ~30 min | $200.00 |

## Rate Limits

| Model | Rate Limit | Impact |
|-------|-----------|--------|
| Free (Qwen 72B via OpenRouter) | 20 RPM | Slow — 240 calls takes ~12 min |
| GPT-4o-mini | 200 RPM | Fast — 240 calls in ~1.5 min |
| Claude Haiku | 200 RPM | Fast — 240 calls in ~1.5 min |
| GPT-4o | 100 RPM | Medium — 240 calls in ~3 min |

Free tier is rate-limited to 20 requests per minute. Paid models run 10x faster.

## Sweet Spot Recommendations

| Use Case | Agents | Model | Cost | Time |
|----------|--------|-------|------|------|
| Quick gut check | 80 | Free (Qwen 72B) | $0 | 12 min |
| Daily workflow | 80 | GPT-4o-mini | $0.05 | 1.5 min |
| Important post | 100 | Claude Haiku | $0.10 | 2 min |
| Deep analysis | 500 | GPT-4o-mini | $0.30 | 8 min |
| Research | 1000 | GPT-4o-mini | $0.60 | 15 min |

**Our recommendation:** Start with 80 agents + GPT-4o-mini. $1/month for 20 battles. Fast enough to run before every post.

## Monthly Assumes

- 5 battles/week × 4 weeks = 20 battles/month
- 3 posts per battle (240 API calls each)
- Concurrent requests capped at 20 (configurable in `config/models.json`)

## Presets

```bash
vibe-check battle --preset free posts/       # $0, slower
vibe-check battle --preset cheap posts/      # GPT-4o-mini, fast
vibe-check battle --preset quality posts/    # Mix: mini for scoring, 4o for interviews
vibe-check battle --preset local posts/      # Ollama, $0, requires local setup
```
