# Ollama Cloud Provider

Run large open-source models in the cloud via Ollama's hosted infrastructure - no local GPU required.

## Quick Start

```bash
# Set API key
export OLLAMA_API_KEY="your-api-key"

# Chat completion
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "gpt-oss:120b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

## Key Features

- **Free Access**: All models available at no cost
- **Large Models**: Run 120B-1T parameter models without local hardware
- **Open Source**: DeepSeek, Qwen, GLM, Kimi, Mistral, and more
- **Ollama Compatible**: Same API as local Ollama

## Model Highlights

| Model | Size | Context | Thinking | Vision | Tools |
|-------|------|---------|----------|--------|-------|
| qwen3.5:397b | 397B | 128K | ❌ | ❌ | ✅ |
| deepseek-v3.2 | 671B | 128K | ❌ | ❌ | ✅ |
| kimi-k2:1t | 1T | 128K | ❌ | ❌ | ✅ |
| kimi-k2-thinking | 1T | 128K | ✅ | ❌ | ❌ |
| qwen3-vl:235b | 235B | 128K | ❌ | ✅ | ❌ |
| mistral-large-3:675b | 675B | 128K | ❌ | ❌ | ✅ |
| gpt-oss:120b | 120B | 128K | ❌ | ❌ | ❌ |
| minimax-m2.5 | 230B | 1M | ❌ | ❌ | ❌ |

## API Protocol

Ollama Cloud uses Ollama's native API format (similar to but not identical to OpenAI).

### Chat Completion

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "stream": false
  }'
```

### Streaming

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "qwen3.5:397b",
    "messages": [{"role": "user", "content": "Write a poem"}],
    "stream": true
  }'
```

### JSON Mode

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "gpt-oss:120b",
    "messages": [{"role": "user", "content": "List 3 colors as JSON"}],
    "format": "json",
    "stream": false
  }'
```

### Vision (Multimodal)

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "qwen3-vl:235b",
    "messages": [{
      "role": "user",
      "content": "Describe this image",
      "images": ["BASE64_ENCODED_IMAGE"]
    }],
    "stream": false
  }'
```

## Model Categories

### Flagship Models (100B+)
- `qwen3.5:397b` - Latest Qwen with tool support
- `deepseek-v3.2` - DeepSeek's V3.2 MoE model
- `kimi-k2:1t` / `kimi-k2.5` - Moonshot's trillion-param model
- `mistral-large-3:675b` - Mistral's largest model

### Code Models
- `qwen3-coder:480b` - Giant code model
- `devstral-2:123b` - Mistral code specialist
- `devstral-small-2:24b` - Smaller code model

### Vision Models
- `qwen3-vl:235b` - Multimodal Qwen
- `qwen3-vl:235b-instruct` - Instruction-tuned vision

### Thinking Models
- `kimi-k2-thinking` - Extended reasoning
- `cogito-2.1:671b` - Deep reasoning model

### Smaller/Faster Models
- `gemma3:4b/12b/27b` - Google's Gemma3
- `ministral-3:3b/8b/14b` - Mistral's small models
- `gpt-oss:20b` - Smaller GPT-OSS

## Python Usage

```python
import requests
import os

def chat(model: str, message: str) -> str:
    response = requests.post(
        "https://ollama.com/api/chat",
        headers={"Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "stream": False
        }
    )
    return response.json()["message"]["content"]

print(chat("gpt-oss:120b", "Hello!"))
```

## Rate Limits

| Metric | Limit |
|--------|-------|
| Requests | ~60/min |
| Tokens | ~100K/min |

## Maintenance

```bash
# Refresh models from API
./update.py --fetch --validate

# View current models
cat config.yaml | grep "id:"
```

## Links

- [Ollama Cloud](https://ollama.com) - Main site
- [Documentation](https://docs.ollama.com/cloud) - API docs
- [API Keys](https://ollama.com/settings/keys) - Get key
- [Local Ollama](https://ollama.com/download) - Self-host alternative
