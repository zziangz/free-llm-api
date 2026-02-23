# Vercel AI Gateway

**Simple Gateway** - Vercel's AI routing proxy for platform deployments.

## Quick Start

```bash
export VERCEL_API_KEY="vck_xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["VERCEL_API_KEY"],
    base_url="https://api.vercel.ai/v1"
)

response = client.chat.completions.create(
    model="auto",  # Gateway auto-selects model
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get an API Key

1. Visit [vercel.com/dashboard](https://vercel.com/dashboard)
2. Go to your project settings
3. Find AI Gateway settings

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/month | 5,000 |

## Notes

- Vercel AI Gateway is mainly for Vercel-deployed applications
- The `auto` model routes to an appropriate backend
- Limited documentation on exact model routing
- Consider using dedicated providers for more control

## Files

| File | Purpose |
|------|---------|
| `config.yaml` | Static config (no API discovery) |
| `metadata.yaml` | Basic metadata |

## Links

- [Vercel AI](https://vercel.com/ai)
- [AI Gateway Docs](https://vercel.com/docs/ai-gateway)
