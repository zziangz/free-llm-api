# OpenRouter

**Model Aggregator** - Access 300+ AI models from multiple providers through one API.

## Quick Start

```bash
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1"
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3-nano-30b-a3b:free",  # Free model
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get an API Key

1. Visit [openrouter.ai](https://openrouter.ai)
2. Create an account
3. Go to **Settings** → **API Keys**

## Free Models

Free models have `:free` suffix. See [config.yaml](config.yaml) for the full list (26 free models).

| Model | Context | Vision | Tools | Description |
|-------|---------|--------|-------|-------------|
| `nvidia/nemotron-3-nano-30b-a3b:free` | 256K | ❌ | ✅ | NVIDIA Nemotron |
| `nvidia/nemotron-nano-12b-v2-vl:free` | 128K | ✅ | ✅ | Vision model |
| `qwen/qwen3-next-80b-a3b-instruct:free` | 131K | ❌ | ✅ | Qwen 3 Next |
| `stepfun/step-3.5-flash:free` | 256K | ❌ | ✅ | StepFun Flash |
| `deepseek/r1-0528:free` | 163K | ❌ | ✅ | DeepSeek R1 |
| `openai/gpt-oss-120b:free` | 131K | ❌ | ✅ | GPT OSS 120B |

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/min | 20 |
| Requests/day | ~50 |

## Registry Maintenance

```bash
# Update free models only
./update.py --fetch --validate

# Include all 300+ models (for reference)
./update.py --fetch --all --validate
```

### Files

| File | Purpose |
|------|---------|
| `config.yaml` | Generated (free models only) |
| `metadata.yaml` | Curated notes |
| `models.json` | Full API cache (300+ models) |
| `update.py` | Config generator |

## Links

- [OpenRouter](https://openrouter.ai)
- [Documentation](https://openrouter.ai/docs)
- [Model List](https://openrouter.ai/models)
