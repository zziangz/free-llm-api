# Groq

**Ultra-Fast Inference** - LPU (Language Processing Unit) technology for blazing fast responses.

## Quick Start

```bash
export GROQ_API_KEY="gsk_xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get an API Key

1. Visit [console.groq.com](https://console.groq.com)
2. Create a free account
3. Go to **API Keys** → Create key

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/min | 30 |
| Tokens/min | 18,000 |
| Requests/day | ~14,400 |

## Models

| Model | Context | Output | Tools | Description |
|-------|---------|--------|-------|-------------|
| `llama-3.3-70b-versatile` | 131K | 32K | ✅ | Best overall |
| `llama-3.1-8b-instant` | 131K | 131K | ✅ | Fast, good quality |
| `openai/gpt-oss-120b` | 131K | 65K | ✅ | OpenAI's open-source model |
| `moonshotai/kimi-k2-instruct-0905` | 262K | 16K | ✅ | Largest context |
| `qwen/qwen3-32b` | 131K | 40K | ✅ | Qwen 3 32B |
| `groq/compound` | 131K | 8K | ✅ | Multi-model agentic |

See [config.yaml](config.yaml) for the full model registry.

## Compound Models

Groq's compound models route between multiple models for optimal results:

```python
response = client.chat.completions.create(
    model="groq/compound",  # Auto-selects best model
    messages=[{"role": "user", "content": "Complex question..."}]
)
```

## Registry Maintenance

```bash
./update.py --fetch --validate
```

### Files

| File | Purpose |
|------|---------|
| `config.yaml` | Generated model registry |
| `metadata.yaml` | Curated capabilities |
| `models.json` | API response cache |
| `update.py` | Config generator |

## Links

- [Groq](https://groq.com)
- [Console](https://console.groq.com)
- [Documentation](https://console.groq.com/docs)
