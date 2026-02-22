# Tokenbank

Free API providers registry for Freeway. This directory contains a curated list of LLM API providers offering free tiers or local inference.

## Structure

```
tokenbank/
├── README.md              # This file
├── schema.json            # JSON Schema for provider validation
├── registry.yaml          # Index of all providers
└── providers/
    ├── cloud/             # Cloud-based free tier providers
    ├── credit-based/      # Providers with trial credits
    └── local/             # Local inference options
```

## Provider Categories

### Cloud (Free Tier)

Providers with recurring free API access:

- GitHub Models
- Google AI Studio
- OpenRouter
- Groq
- Cerebras
- Together AI
- DeepSeek
- Mistral
- NVIDIA NIM
- Vercel AI Gateway

### Credit-Based

Providers offering trial credits:

- Hyperbolic ($1 credit)
- Nebius ($1 credit)
- SambaNova ($5 for 3 months)

### Local

Local inference options (no rate limits):

- Ollama
- vLLM
- LM Studio

## Provider Format

Each provider is defined in a YAML file following this structure:

```yaml
$id: "provider-id"
name: "Provider Name"
description: "Brief description"
url: "https://provider.url"
docs: "https://docs.url"

auth:
  type: "bearer"          # bearer, query, header, or none
  keyLabel: "API Key"
  keyUrl: "https://get-key.url"
  keyPrefix: "sk-"        # Optional validation hint
  keyParam: "key"         # For query/header auth types

endpoint:
  baseUrl: "https://api.provider.com/v1"
  protocol: "openai"      # openai, ollama, anthropic, gemini, custom

limits:
  requestsPerMinute: 60
  tokensPerDay: 100000

models:
  - id: "model-id"
    upstream: "actual-model-name"
    free: true
    modalities:
      - text-to-text
      - text-image-to-text
    contextWindow: 128000
    capabilities:
      streaming: true
      tools: true
      vision: true
      json: true

status: "active"
tags: ["free", "rate-limited"]
```

## Modality Types

| Modality | Input | Output | Examples |
|----------|-------|--------|----------|
| `text-to-text` | Text | Text | GPT-4, Llama, Claude |
| `text-image-to-text` | Text + Image | Text | GPT-4o, Gemini Vision |
| `image-to-text` | Image | Text | BLIP, LLaVA |
| `text-to-image` | Text | Image | Stable Diffusion, Flux |
| `image-to-image` | Image | Image | SD img2img, ControlNet |
| `text-to-audio` | Text | Audio | TTS models |
| `audio-to-text` | Audio | Text | Whisper |
| `text-to-embedding` | Text | Vector | text-embedding-3 |
| `text-to-video` | Text | Video | Sora |
| `video-to-text` | Video | Text | Video models |

## Integration with Freeway

Freeway reads the tokenbank to:

1. Discover available providers
2. Auto-configure endpoints from provider definitions
3. Track API key status per provider
4. Import free-tier models automatically

API keys are stored in `~/.config/freeway/config.yaml`, not in environment variables:

```yaml
providers:
  github-models:
    apiKey: "ghp_xxx"
    enabled: true
  
  local-ollama:
    enabled: false
    baseUrl: "http://localhost:11434"
```

## Adding Providers

To add a new provider:

1. Create a YAML file in the appropriate category directory
2. Follow the schema defined in `schema.json`
3. Validate using: `freeway providers validate <file>`
4. Submit a pull request

## License

MIT
