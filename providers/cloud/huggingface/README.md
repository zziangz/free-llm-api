# HuggingFace Inference Router

**Unified Gateway** - Access 126 models from 15+ inference providers through one API.

> ⚠️ **Free Tier Warning**: HuggingFace's own credits are very limited ($0.10/month).
> For truly free usage, use dedicated providers like [Cerebras](../cerebras/), [Groq](../groq/), or [SambaNova](../../credit-based/sambanova.yaml) directly.

## Quick Start

```bash
# Set your HuggingFace token
export HF_TOKEN="hf_xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["HF_TOKEN"],
    base_url="https://router.huggingface.co/v1"
)

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get a Token

1. Visit [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a new token (read access is sufficient)
3. Set as `HF_TOKEN` environment variable

## Free Tier Limitations

| Resource | Limit |
|----------|-------|
| Monthly Credits | $0.10 |
| After that | Pay-as-you-go |

**For free usage**, the router can route to free providers:
- **Cerebras** - Fast inference, select models
- **Groq** - Fast inference, Llama/Qwen models  
- **SambaNova** - High throughput
- **Hyperbolic** - Various models

Check `freeVia` field in [config.yaml](config.yaml) for models with free routing.

## Backend Providers

The router aggregates these inference providers:

| Provider | Type | Notes |
|----------|------|-------|
| `hf-inference` | HF's own | Limited free tier |
| `cerebras` | Free | We have [dedicated config](../cerebras/) |
| `groq` | Free | We have [dedicated config](../groq/) |
| `sambanova` | Free | We have [dedicated config](../../credit-based/sambanova.yaml) |
| `hyperbolic` | Free | We have [dedicated config](../../credit-based/hyperbolic.yaml) |
| `novita` | Paid | Many models |
| `together` | Paid | [Together AI](https://together.ai) |
| `fireworks-ai` | Paid | [Fireworks](https://fireworks.ai) |
| `cohere` | Paid | [Cohere](https://cohere.com) |

## Notable Models

| Model | Context | Vision | Tools | Free Via |
|-------|---------|--------|-------|----------|
| `meta-llama/Llama-3.3-70B-Instruct` | 128K | ❌ | ✅ | groq |
| `Qwen/Qwen3-235B-A22B-Thinking-2507` | 262K | ❌ | ✅ | cerebras |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | 128K | ✅ | ✅ | - |
| `Qwen/Qwen3.5-397B-A17B` | 262K | ✅ | ✅ | - |
| `mistralai/Mistral-Large-Instruct-2411` | 128K | ❌ | ✅ | - |

See [config.yaml](config.yaml) for the full model registry (126 models).

## When to Use HuggingFace Router

✅ **Good for:**
- Unified API access to many models
- Comparing models across providers
- Automatic provider failover
- HuggingFace ecosystem integration

❌ **Better alternatives for:**
- Free unlimited usage → Use Cerebras, Groq directly
- Maximum speed → Use provider directly
- Specific provider features → Use provider directly

## Vision Example

```python
response = client.chat.completions.create(
    model="meta-llama/Llama-3.2-90B-Vision-Instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
)
```

## Registry Maintenance

```bash
# Fetch latest models from router API
./update.py --fetch --validate
```

### Files

| File | Purpose |
|------|---------|
| `config.yaml` | **Generated** - Main model registry |
| `metadata.yaml` | **Curated** - Provider notes, recommendations |
| `models.json` | **Cached** - API response snapshot |
| `update.py` | **Script** - Config generator |
| `openapi.json` | **Reference** - Hub API spec (not router) |

## Links

- [HuggingFace Hub](https://huggingface.co)
- [Inference API Docs](https://huggingface.co/docs/api-inference/index)
- [Token Settings](https://huggingface.co/settings/tokens)
- [Pricing](https://huggingface.co/pricing)
