# Cerebras

**Wafer Scale Engine** - Ultra-fast inference using custom silicon.

## Quick Start

```bash
export CEREBRAS_API_KEY="csk-xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["CEREBRAS_API_KEY"],
    base_url="https://api.cerebras.ai/v1"
)

response = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get an API Key

1. Visit [cloud.cerebras.ai](https://cloud.cerebras.ai/platform/)
2. Create a free account
3. Generate an API key

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/min | 30 |
| Requests/hour | 900 |
| Tokens/min | 60,000 |

## Models

| Model | Context | Output | Description |
|-------|---------|--------|-------------|
| `gpt-oss-120b` | 65K | 8K | OpenAI's open-source model |
| `qwen-3-235b-a22b-instruct-2507` | 131K | 16K | Qwen 3 235B |
| `zai-glm-4.7` | 128K | 8K | GLM 4.7 |
| `llama3.1-8b` | 65K | 8K | Fast, efficient |

See [config.yaml](config.yaml) for the full model registry.

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

- [Cerebras](https://cerebras.ai)
- [Cloud Platform](https://cloud.cerebras.ai)
- [Documentation](https://cloud.cerebras.ai/platform/docs)
