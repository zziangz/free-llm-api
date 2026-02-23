# Google AI Studio (Gemini) Provider

Google's Gemini models with massive context windows, multimodal support, and state-of-the-art reasoning capabilities.

## Quick Start

```bash
# Set API key
export GEMINI_API_KEY="your-api-key"

# Using curl (native Gemini API)
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "Hello!"}]}]}'
```

## Key Features

- **1M+ Context Window**: Industry-leading context (up to 1,048,576 tokens)
- **Multimodal**: Native image, audio, and video understanding
- **Thinking Models**: Gemini 2.5 series with extended reasoning
- **Free Tier**: 15 RPM, 1M tokens/min for all models
- **Function Calling**: Built-in tool support

## Model Highlights

| Model | Context | Output | Thinking | Vision |
|-------|---------|--------|----------|--------|
| gemini-2.5-flash | 1M | 65K | ✅ | ✅ |
| gemini-2.5-pro | 1M | 65K | ✅ | ✅ |
| gemini-2.0-flash | 1M | 8K | ❌ | ✅ |
| gemma-3-27b-it | 128K | 8K | ❌ | ✅ |

## API Protocol

> ⚠️ Gemini uses a **custom protocol**, not OpenAI-compatible.

### Key Differences

| Aspect | OpenAI | Gemini |
|--------|--------|--------|
| Auth | Bearer header | Query param `?key=` |
| Endpoint | `/v1/chat/completions` | `/v1beta/models/{model}:generateContent` |
| Messages | `{"role": "user", "content": "..."}` | `{"contents": [{"parts": [{"text": "..."}]}]}` |
| Streaming | SSE chunks | Chunked JSON |

### Native Request

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{"text": "Explain quantum computing"}]
    }]
  }'
```

### With System Prompt

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "systemInstruction": {"parts": [{"text": "You are a helpful assistant"}]},
    "contents": [{
      "parts": [{"text": "Hello!"}]
    }]
  }'
```

### Streaming

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "Write a poem"}]}]}'
```

### Vision (Image)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        {"text": "Describe this image"},
        {"inlineData": {"mimeType": "image/jpeg", "data": "BASE64_DATA"}}
      ]
    }]
  }'
```

## OpenAI SDK Compatibility

Google provides an OpenAI-compatible endpoint:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Rate Limits (Free Tier)

| Metric | Limit |
|--------|-------|
| Requests | 15/min |
| Tokens | 1,000,000/min |

## Model Categories

- **Thinking models**: gemini-2.5-flash, gemini-2.5-pro (extended reasoning)
- **Fast models**: gemini-2.0-flash family (optimized for speed)
- **Gemma OSS**: gemma-3-* (open-source, self-hostable)
- **Legacy**: gemini-1.5-pro/flash, gemini-1.0-pro

## Maintenance

```bash
# Refresh models from API
./update.py --fetch --validate

# View current models
cat config.yaml | grep "id:"
```

## Links

- [AI Studio](https://aistudio.google.com) - Playground
- [API Keys](https://aistudio.google.com/api-keys) - Get key
- [Documentation](https://ai.google.dev/docs) - Full docs
- [Pricing](https://ai.google.dev/pricing) - Usage tiers
