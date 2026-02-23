# Mistral AI Provider

**OpenAI-Compatible** - Mistral API uses the OpenAI protocol directly. No adapter needed.

## Quick Start

```bash
# Set your API key
export MISTRAL_API_KEY="your-key-here"

# Use with OpenAI SDK (Python)
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MISTRAL_API_KEY"],
    base_url="https://api.mistral.ai/v1"
)

response = client.chat.completions.create(
    model="mistral-medium-latest",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

```bash
# Or with curl
curl https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-medium-latest", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## Get an API Key

1. Visit [console.mistral.ai](https://console.mistral.ai)
2. Create a free account
3. Go to **API Keys** → **Create new key**

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/min | 1 |
| Tokens/min | 500,000 |
| Tokens/month | 1 billion |

## Models

| Model | Context | Vision | Tools | Description |
|-------|---------|--------|-------|-------------|
| `mistral-medium-latest` | 131K | ✅ | ✅ | Frontier multimodal model (May 2025) |
| `mistral-small-latest` | 32K | ✅ | ✅ | Best balance of speed and capability |
| `pixtral-large-latest` | 131K | ✅ | ✅ | Large vision model |
| `codestral-latest` | 32K | ❌ | ✅ | Code generation with FIM |
| `ministral-8b-latest` | 131K | ❌ | ✅ | Edge-optimized 8B model |
| `ministral-3b-latest` | 131K | ❌ | ✅ | Edge-optimized 3B model |

See [config.yaml](config.yaml) for the full model registry.

## Special Features

### Vision (Pixtral)
```python
response = client.chat.completions.create(
    model="pixtral-large-latest",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
)
```

### Fill-in-the-Middle (Codestral)
```python
response = client.completions.create(
    model="codestral-latest",
    prompt="def fibonacci(n):",
    suffix="\n    return fib(n-1) + fib(n-2)"
)
```

### Function Calling
```python
response = client.chat.completions.create(
    model="mistral-medium-latest",
    messages=[{"role": "user", "content": "What's the weather?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}
        }
    }]
)
```

## Registry Maintenance

### Updating Models
```bash
# Fetch latest models from API (requires MISTRAL_API_KEY)
./update.py --fetch --validate

# Or use curl manually if Python SSL issues
source ../../../.env
curl -s 'https://api.mistral.ai/v1/models' -H "Authorization: Bearer $MISTRAL_API_KEY" > models.json
./update.py --validate
```

### Files

| File | Purpose |
|------|---------|
| `config.yaml` | **Generated** - Main model registry |
| `metadata.yaml` | **Curated** - Manual capability overrides |
| `models.json` | **Cached** - API response snapshot |
| `update.py` | **Script** - Config generator |

## Links

- [Mistral AI](https://mistral.ai)
- [Documentation](https://docs.mistral.ai)
- [API Console](https://console.mistral.ai)
- [Model Overview](https://docs.mistral.ai/getting-started/models/models_overview)
