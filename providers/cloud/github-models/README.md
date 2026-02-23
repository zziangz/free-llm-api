# GitHub Models

**Free for GitHub Users** - Access GPT-4o, Llama, Mistral and more via Azure AI.

## Quick Start

```bash
export GITHUB_PERSONAL_TOKEN="ghp_xxxxxxxxxxxxx"
```

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GITHUB_PERSONAL_TOKEN"],
    base_url="https://models.inference.ai.azure.com"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Get a Token

1. Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new)
2. Create a new fine-grained token
3. No special permissions needed for GitHub Models

## Free Tier Limits

| Limit | Value |
|-------|-------|
| Requests/min | 60 |
| Tokens/day | 100,000 |
| Concurrent | 5 |

## Models

| Model | Context | Vision | Tools | Publisher |
|-------|---------|--------|-------|-----------|
| `gpt-4o` | 128K | ✅ | ✅ | Azure OpenAI |
| `gpt-4o-mini` | 128K | ✅ | ✅ | Azure OpenAI |
| `Meta-Llama-3.1-405B-Instruct` | 131K | ❌ | ✅ | Meta |
| `Meta-Llama-3.1-70B-Instruct` | 131K | ❌ | ✅ | Meta |
| `Meta-Llama-3.1-8B-Instruct` | 131K | ❌ | ✅ | Meta |
| `Mistral-large-2407` | 131K | ❌ | ✅ | Mistral |
| `Mistral-Nemo` | 131K | ❌ | ❌ | Mistral |
| `AI21-Jamba-Instruct` | 256K | ❌ | ❌ | AI21 Labs |

See [config.yaml](config.yaml) for the full model registry.

## Vision Example

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
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

- [GitHub Models Marketplace](https://github.com/marketplace/models)
- [Documentation](https://docs.github.com/en/github-models)
