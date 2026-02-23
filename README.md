# Free LLM API Providers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Providers](https://img.shields.io/badge/providers-11-blue)](providers/cloud/)
[![Models](https://img.shields.io/badge/models-390%2B-green)](registry.yaml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](PROVIDER_STRUCTURE.md)

This repository is inspired by [Cheahjs's repo](https://github.com/cheahjs/free-llm-api-resources). Instead of documenting the providers in the README markdown file, we maintain a structured registry of providers in YAML format. One may use this registry to make a pool of free LLM tokens available for various applications, such as [Freeway](https://github.com/zziangz/freeway). The registry is designed to be easily extendable and maintainable, allowing the community to contribute new providers and keep the information up-to-date.

Feel free to create pull requests to add new providers, update model information, or improve documentation. Alternatively, you can open issues to suggest changes or report inaccuracies. Our goal is to build a comprehensive and reliable resource for free LLM API providers that anyone can use and contribute to.

## Scope & Criteria

We focus on **truly free** LLM API providers. To be included, a provider must meet these criteria:

| Requirement | Description |
|-------------|-------------|
| **No payment method required** | No credit card or deposit needed to access free tier |
| **Recurring limits** | Token/request limits that refill automatically (daily, monthly, etc.) |
| **API access** | Programmatic access via REST API, not just web UI |
| **Currently active** | Provider is operational and accepting new signups |

### Excluded Providers

Some providers offer "free" tiers but require deposits or payment methods:

| Provider | Reason for Exclusion |
|----------|---------------------|
| **Together.ai** | Requires $5 minimum deposit |

These are excluded to maintain our strict definition of "free" - providers that anyone can use without financial commitment.

## Challenges

The trivial part is to get the model card for every model from providers. Not all providers provide model metadata through their API, actually, only openRouter does.

### Solution: Multi-Source Metadata Approach

We've developed a hybrid approach combining multiple data sources:

1. **API-First (Ideal):** Providers like OpenRouter expose complete model metadata via API
   - Capabilities, modalities, context windows, pricing
   - Can be directly mapped to our registry format

2. **API + Curated Metadata (NVIDIA NIM Example):**
   - NVIDIA's API provides only basic info: `{id, object, created, owned_by}`
   - We maintain a curated `metadata.yaml` with:
     - Vision/multimodal capabilities (17 models)
     - Context window sizes (120+ custom configs)
     - Tool/function calling support (37 no-tool models)
     - Use cases and model categories
   - Enhanced parser combines API data + curated metadata + heuristics
   - See `providers/cloud/nvidia-nim/` for implementation

3. **Manual Curation (Fallback):**
   - For providers without APIs: manual documentation review
   - Periodic updates from provider changelogs
   - Community contributions via PRs

Each provider's discovery code is organized in `providers/cloud/{provider-name}/` with:
- `metadata.yaml` - Curated model capabilities
- `models.json` - Raw API response (if available)
- `update.py` - Parser/generator script
- `README.md` - Provider-specific documentation

**For detailed documentation on the provider folder structure and how to add new providers, see [PROVIDER_STRUCTURE.md](PROVIDER_STRUCTURE.md).**

## Structure

```
free-llm-api/
├── README.md              # This file
├── PROVIDER_STRUCTURE.md  # How to add new providers
├── schema.json            # JSON Schema for provider validation
├── registry.yaml          # Index of all providers
└── providers/
    └── cloud/             # Free cloud API providers
        ├── cerebras/
        ├── cloudflare/
        ├── gemini/
        ├── github-models/
        ├── groq/
        ├── huggingface/
        ├── mistral/
        ├── nvidia-nim/
        ├── ollama-cloud/
        ├── openrouter/
        └── vercel-ai/
```

Each provider folder contains:
- `config.yaml` - Provider configuration and model list
- `metadata.yaml` - Curated model capabilities
- `models.json` - Cached API response (gitignored)
- `update.py` - Auto-updater script
- `README.md` - Provider documentation
- `adapter.py` - Protocol adapter (optional, for non-OpenAI providers)

### Python Scripts

Each provider includes an `update.py` script for maintaining the model registry:

```bash
cd providers/cloud/groq

# Generate config.yaml from cached models.json
./update.py

# Fetch latest models from API and regenerate
./update.py --fetch

# Validate the generated config
./update.py --validate
```

For providers with non-OpenAI protocols (e.g., Cloudflare, Gemini), an `adapter.py` provides OpenAI SDK compatibility:

```python
# Example: Using Cloudflare with OpenAI SDK
from providers.cloud.cloudflare.adapter import CloudflareAdapter

client = CloudflareAdapter()
response = client.chat.completions.create(
    model="@cf/meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Providers

| Provider | Models | Protocol | RPM | RPD | TPM | TPD | Highlights |
|----------|--------|----------|-----|-----|-----|-----|------------|
| [Cerebras](providers/cloud/cerebras/) | 4 | OpenAI | 30 | 14K | 60K | 1.0M | Ultra-fast inference, GLM-4.7 |
| [Cloudflare](providers/cloud/cloudflare/) | 74 | Custom | - | - | - | - | Workers AI, image gen, embeddings |
| [Gemini](providers/cloud/gemini/) | 8 | Gemini | * | * | * | * | 1M context, multimodal, 2.5 Pro/Flash |
| [GitHub Models](providers/cloud/github-models/) | 26 | OpenAI | 60 | - | - | 100K | GPT-4.1, Grok-3, DeepSeek-R1 |
| [Groq](providers/cloud/groq/) | 12 | OpenAI | 30 | 14K | 18K | 1.0M | Fastest inference, Kimi-K2 |
| [HuggingFace](providers/cloud/huggingface/) | 126 | OpenAI | - | - | - | - | 126 open-source models |
| [Mistral](providers/cloud/mistral/) | 40 | OpenAI | 1 | - | 500K | - | Codestral, agents, 500K TPM |
| [NVIDIA NIM](providers/cloud/nvidia-nim/) | 167 | OpenAI | 30 | 1K | - | - | 167 models, enterprise |
| [Ollama Cloud](providers/cloud/ollama-cloud/) | 32 | Ollama | 60 | - | 100K | - | 32 large OSS models |
| [OpenRouter](providers/cloud/openrouter/) | 26 | OpenAI | 20 | 50 | - | - | Multi-provider gateway |
| [Vercel AI](providers/cloud/vercel-ai/) | 1 | OpenAI | - | - | - | - | Auto model routing |

> **Rate Limits:** RPM = Requests/Minute, RPD = Requests/Day, TPM = Tokens/Minute, TPD = Tokens/Day  
> \* Gemini has per-model rate limits (see provider docs)

## Top Models by Benchmark

Models sorted by [LiveBench](https://livebench.ai) scores. **Pooled limits** show combined rate limits when using the same model across multiple providers.

| Model | Score | Providers | Pooled RPM | Pooled RPD | Context | Vision | Tools |
|-------|-------|-----------|------------|------------|---------|--------|-------|
| **GPT-4.1** | 68.0 | github-models | 180 | - | 128K | ✓ | ✓ |
| **GPT-4o** | 65.0 | github-models | 60 | - | 128K | ✓ | ✓ |
| **Gemini 2.5 Flash** | 64.0 | gemini | * | * | 1M | ✓ | ✓ |
| **Grok-3** | 62.0 | github-models | 60 | - | 128K | - | ✓ |
| **GLM-4.7** | 58.1 | cerebras, cloudflare, nvidia-nim, ollama-cloud | 120 | 15K | 131K | - | ✓ |
| **DeepSeek-R1** | 57.0 | github-models, huggingface, nvidia-nim, ollama-cloud, openrouter | 260 | 4K | 164K | - | ✓ |
| **DeepSeek-V3** | 55.0 | github-models, huggingface, nvidia-nim, openrouter | 270 | 3K | 164K | - | ✓ |
| **Qwen3 235B** | 53.0 | cerebras, huggingface, nvidia-nim, ollama-cloud | 180 | 15K | 262K | ✓ | ✓ |
| **Kimi-K2** | 48.1 | groq, huggingface, nvidia-nim, ollama-cloud | 360 | 33K | 262K | ✓ | ✓ |
| **GPT-OSS 120B** | 46.1 | cerebras, groq, huggingface, nvidia-nim, ollama-cloud, openrouter | 170 | 30K | 131K | - | ✓ |
| **Llama 3.3 70B** | 45.0 | cloudflare, github-models, groq, nvidia-nim, ollama-cloud, openrouter | 140 | 15K | 131K | - | ✓ |
| **Mistral Large** | 44.0 | mistral, nvidia-nim, ollama-cloud | 151 | 3K | 262K | ✓ | ✓ |
| **Llama 3.1 70B** | 43.0 | cloudflare, nvidia-nim | 90 | 3K | 131K | - | ✓ |
| **Codestral** | 42.0 | mistral, nvidia-nim | 61 | 2K | 256K | - | ✓ |
| **Phi-4** | 38.0 | github-models, nvidia-nim | 390 | 3K | 128K | ✓ | ✓ |
| **Llama 3.1 8B** | 33.0 | cerebras, cloudflare, github-models, groq, huggingface, nvidia-nim | 150 | 30K | 131K | - | ✓ |

> **Note:** Vision = Image input support, Tools = Function calling support

## Provider Format

Each provider is defined in a `config.yaml` file following this structure:

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
  protocol: "openai"      # openai, ollama, gemini, cloudflare, custom

limits:
  requests:
    perMinute: 60
    perDay: 1000
  tokens:
    perMinute: 100000

models:
  - id: "model-id"
    upstream: "actual-model-name"
    free: true
    modalities:
      - text-to-text
      - image-to-text
    contextWindow: 128000
    maxOutputTokens: 8192
    capabilities:
      streaming: true
      tools: true
      vision: true
      json: true

status: "active"
env: "PROVIDER_API_KEY"
tags: ["free", "rate-limited"]
```

## Modality Types

| Modality | Input | Output | Examples |
|----------|-------|--------|----------|
| `text-to-text` | Text | Text | GPT-4, Llama, Claude |
| `image-to-text` | Text + Image | Text | GPT-4o, Gemini Vision, Llava |
| `text-to-image` | Text | Image | Stable Diffusion, Flux |
| `text-to-audio` | Text | Audio | TTS models |
| `audio-to-text` | Audio | Text | Whisper |
| `text-to-embedding` | Text | Vector | text-embedding-3 |
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
  
  groq:
    apiKey: "gsk_xxx"
    enabled: true
```

## Adding Providers

To add a new provider:

1. Create a folder in `providers/cloud/{provider-name}/`
2. Add `config.yaml`, `metadata.yaml`, `update.py`, `README.md`
3. Follow the schema defined in `schema.json`
4. See [PROVIDER_STRUCTURE.md](PROVIDER_STRUCTURE.md) for detailed guide
5. Submit a pull request

## Acknowledgements

- [free-llm.com](https://free-llm.com/) - Comprehensive resource for free LLM providers and tips
- [Cheahjs's free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) - Original inspiration for this project

## License

MIT
