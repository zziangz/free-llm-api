# Cloudflare Workers AI

Cloudflare Workers AI lets you run AI models at the edge with generous free tier limits.

## Setup

### 1. Get your credentials

You need two pieces of information:

1. **API Token**: Create at https://dash.cloudflare.com/profile/api-tokens
   - Use the "Workers AI" template or create a custom token with `Workers AI:Read` permission

2. **Account ID**: Find at https://dash.cloudflare.com/
   - Click any zone → Overview → right sidebar shows "Account ID"

### 2. Configure environment

Add to your `.env` file in the project root:

```bash
CLOUDFLARE_AI_API_KEY=your-api-token
CLOUDFLARE_AI_ACCOUNT_ID=your-account-id
```

The adapter automatically loads `.env` from the project root — no need to export manually.

## Usage

### Option 1: OpenAI-Compatible Adapter (Recommended)

Use the adapter for seamless OpenAI SDK compatibility:

```python
from adapter import CloudflareAdapter

client = CloudflareAdapter()

# Chat completions
response = client.chat.completions.create(
    model="@cf/meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)

# Streaming
for chunk in client.chat.completions.create(
    model="@cf/meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
):
    print(chunk["choices"][0]["delta"].get("content", ""), end="")

# Embeddings
embeddings = client.embeddings.create(
    model="@cf/baai/bge-base-en-v1.5",
    input="Hello world"
)
```

### Option 2: Proxy Server Mode

Run the adapter as an OpenAI-compatible proxy:

```bash
python adapter.py --serve --port 8080
```

Then use any OpenAI-compatible tool:

```python
from openai import OpenAI

client = OpenAI(
    api_key="unused",  # Auth handled by proxy
    base_url="http://localhost:8080/v1"
)

response = client.chat.completions.create(
    model="@cf/meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Option 3: Native API (Direct)

Cloudflare's native API format (not OpenAI-compatible):

```bash
curl https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_AI_ACCOUNT_ID/ai/run/@cf/meta/llama-3-8b-instruct \
  -H "Authorization: Bearer $CLOUDFLARE_AI_API_KEY" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'
```

## Protocol Specification

The `protocol.yaml` file defines a declarative translation layer between OpenAI-compatible requests and Cloudflare's native API. This allows any tool to automatically adapt to Cloudflare's custom format.

### Protocol Format

```yaml
# Which format clients send vs what the API expects
baseProtocol: "openai"
targetProtocol: "cloudflare-workers-ai"

# Required environment variables
env:
  CLOUDFLARE_AI_API_KEY: { required: true }
  CLOUDFLARE_AI_ACCOUNT_ID: { required: true }

# URL template with variable substitution
url:
  template: "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
  variables:
    account_id: { source: "env", key: "CLOUDFLARE_AI_ACCOUNT_ID" }
    model: { source: "request.model" }

# Request body transformation
request:
  body:
    passthrough: ["messages", "temperature", "max_tokens", "stream"]
    remove: ["model"]  # Model goes in URL path, not body

# Response transformation
response:
  sync:
    mapping:
      choices[0].message.content: { source: "response.result.response" }
  stream:
    input_field: "response"
    output_path: "choices[0].delta.content"
```

### Key Transformations

| OpenAI Format | Cloudflare Format |
|--------------|-------------------|
| `POST /v1/chat/completions` | `POST /accounts/{id}/ai/run/{model}` |
| `{"model": "...", "messages": [...]}` | `{"messages": [...]}` (model in URL) |
| `{"choices": [{"message": {"content": "..."}}]}` | `{"result": {"response": "..."}}` |
| `data: {"choices": [{"delta": {"content": "token"}}]}` | `data: {"response": "token"}` |

### Using the Protocol Spec

The `adapter.py` reads `protocol.yaml` and provides:
- **Python module**: `CloudflareAdapter()` with OpenAI-compatible interface
- **Proxy server**: `python adapter.py --serve --port 8080`
- **Auto-loads `.env`**: No manual env setup needed

## Updating Models

```bash
pip install requests pyyaml

python update.py                # Generate from curated list
python update.py --fetch        # Fetch from Cloudflare docs
python update.py --validate     # Validate output
```

## File Structure

| File | Purpose |
|------|---------|
| `config.yaml` | Main provider config (generated) |
| `protocol.yaml` | OpenAI↔Cloudflare translation spec |
| `adapter.py` | OpenAI-compatible Python adapter |
| `metadata.yaml` | Curated model capabilities |
| `models.json` | Cached model data |
| `update.py` | Config generator script |

## Pricing

It uses a "Neurons" model to measure the cost, of course, we are the absolute-free users. We have 
|	Free allocation	| Pricing |
| -- | -- |
|Workers Free	10,000 Neurons per day	| N/A - Upgrade to Workers Paid |

Here is a paste of the neuron measurement
LLM model pricing
Model	Price in Tokens	Price in Neurons
@cf/meta/llama-3.2-1b-instruct	$0.027 per M input tokens
$0.201 per M output tokens	2457 neurons per M input tokens
18252 neurons per M output tokens
@cf/meta/llama-3.2-3b-instruct	$0.051 per M input tokens
$0.335 per M output tokens	4625 neurons per M input tokens
30475 neurons per M output tokens
@cf/meta/llama-3.1-8b-instruct-fp8-fast	$0.045 per M input tokens
$0.384 per M output tokens	4119 neurons per M input tokens
34868 neurons per M output tokens
@cf/meta/llama-3.2-11b-vision-instruct	$0.049 per M input tokens
$0.676 per M output tokens	4410 neurons per M input tokens
61493 neurons per M output tokens
@cf/meta/llama-3.1-70b-instruct-fp8-fast	$0.293 per M input tokens
$2.253 per M output tokens	26668 neurons per M input tokens
204805 neurons per M output tokens
@cf/meta/llama-3.3-70b-instruct-fp8-fast	$0.293 per M input tokens
$2.253 per M output tokens	26668 neurons per M input tokens
204805 neurons per M output tokens
@cf/deepseek-ai/deepseek-r1-distill-qwen-32b	$0.497 per M input tokens
$4.881 per M output tokens	45170 neurons per M input tokens
443756 neurons per M output tokens
@cf/mistral/mistral-7b-instruct-v0.1	$0.110 per M input tokens
$0.190 per M output tokens	10000 neurons per M input tokens
17300 neurons per M output tokens
@cf/mistralai/mistral-small-3.1-24b-instruct	$0.351 per M input tokens
$0.555 per M output tokens	31876 neurons per M input tokens
50488 neurons per M output tokens
@cf/meta/llama-3.1-8b-instruct	$0.282 per M input tokens
$0.827 per M output tokens	25608 neurons per M input tokens
75147 neurons per M output tokens
@cf/meta/llama-3.1-8b-instruct-fp8	$0.152 per M input tokens
$0.287 per M output tokens	13778 neurons per M input tokens
26128 neurons per M output tokens
@cf/meta/llama-3.1-8b-instruct-awq	$0.123 per M input tokens
$0.266 per M output tokens	11161 neurons per M input tokens
24215 neurons per M output tokens
@cf/meta/llama-3-8b-instruct	$0.282 per M input tokens
$0.827 per M output tokens	25608 neurons per M input tokens
75147 neurons per M output tokens
@cf/meta/llama-3-8b-instruct-awq	$0.123 per M input tokens
$0.266 per M output tokens	11161 neurons per M input tokens
24215 neurons per M output tokens
@cf/meta/llama-2-7b-chat-fp16	$0.556 per M input tokens
$6.667 per M output tokens	50505 neurons per M input tokens
606061 neurons per M output tokens
@cf/meta/llama-guard-3-8b	$0.484 per M input tokens
$0.030 per M output tokens	44003 neurons per M input tokens
2730 neurons per M output tokens
@cf/meta/llama-4-scout-17b-16e-instruct	$0.270 per M input tokens
$0.850 per M output tokens	24545 neurons per M input tokens
77273 neurons per M output tokens
@cf/google/gemma-3-12b-it	$0.345 per M input tokens
$0.556 per M output tokens	31371 neurons per M input tokens
50560 neurons per M output tokens
@cf/qwen/qwq-32b	$0.660 per M input tokens
$1.000 per M output tokens	60000 neurons per M input tokens
90909 neurons per M output tokens
@cf/qwen/qwen2.5-coder-32b-instruct	$0.660 per M input tokens
$1.000 per M output tokens	60000 neurons per M input tokens
90909 neurons per M output tokens
@cf/qwen/qwen3-30b-a3b-fp8	$0.051 per M input tokens
$0.335 per M output tokens	4625 neurons per M input tokens
30475 neurons per M output tokens
@cf/openai/gpt-oss-120b	$0.350 per M input tokens
$0.750 per M output tokens	31818 neurons per M input tokens
68182 neurons per M output tokens
@cf/openai/gpt-oss-20b	$0.200 per M input tokens
$0.300 per M output tokens	18182 neurons per M input tokens
27273 neurons per M output tokens
@cf/aisingapore/gemma-sea-lion-v4-27b-it	$0.351 per M input tokens
$0.555 per M output tokens	31876 neurons per M input tokens
50488 neurons per M output tokens
@cf/ibm-granite/granite-4.0-h-micro	$0.017 per M input tokens
$0.112 per M output tokens	1542 neurons per M input tokens
10158 neurons per M output tokens
@cf/zai-org/glm-4.7-flash	$0.060 per M input tokens
$0.400 per M output tokens	5500 neurons per M input tokens
36400 neurons per M output tokens
Embeddings model pricing
Model	Price in Tokens	Price in Neurons
@cf/baai/bge-small-en-v1.5	$0.020 per M input tokens	1841 neurons per M input tokens
@cf/baai/bge-base-en-v1.5	$0.067 per M input tokens	6058 neurons per M input tokens
@cf/baai/bge-large-en-v1.5	$0.204 per M input tokens	18582 neurons per M input tokens
@cf/baai/bge-m3	$0.012 per M input tokens	1075 neurons per M input tokens
@cf/pfnet/plamo-embedding-1b	$0.019 per M input tokens	1689 neurons per M input tokens
@cf/qwen/qwen3-embedding-0.6b	$0.012 per M input tokens	1075 neurons per M input tokens
Image model pricing
Model	Price in Tokens	Price in Neurons
@cf/black-forest-labs/flux-1-schnell	$0.0000528 per 512x512 tile
$0.0001056 per step	4.80 neurons per 512x512 tile
9.60 neurons per step
@cf/leonardo/lucid-origin	$0.006996 per 512x512 tile
$0.000132 per step	636.00 neurons per 512x512 tile
12.00 neurons per step
@cf/leonardo/phoenix-1.0	$0.005830 per 512x512 tile
$0.000110 per step	530.00 neurons per 512x512 tile
10.00 neurons per step
@cf/black-forest-labs/flux-2-dev	$0.00021 per input 512x512 tile, per step
$0.00041 per output 512x512 tile, per step	18.75 neurons per input 512x512 tile, per step
37.50 neurons per output 512x512 tile, per step
@cf/black-forest-labs/flux-2-klein-4b	$0.000059 per input 512x512 tile
$0.000287 per output 512x512 tile	5.37 neurons per input 512x512 tile
26.05 neurons per output 512x512 tile
@cf/black-forest-labs/flux-2-klein-9b	$0.015 per first MP (1024x1024)
$0.002 per subsequent MP
$0.002 per input image MP	1363.64 neurons per first MP (1024x1024)
181.82 neurons per subsequent MP
181.82 neurons per input image MP
Audio model pricing
Model	Price in Tokens	Price in Neurons
@cf/openai/whisper	$0.0005 per audio minute	41.14 neurons per audio minute
@cf/openai/whisper-large-v3-turbo	$0.0005 per audio minute	46.63 neurons per audio minute
@cf/myshell-ai/melotts	$0.0002 per audio minute	18.63 neurons per audio minute
@cf/deepgram/aura-1	$0.015 per 1k characters input
1,363.64 neurons per 1k characters input
@cf/deepgram/nova-3	$0.0052 per audio minute input
472.73 neurons per audio minute input
@cf/deepgram/nova-3 (WebSocket)	$0.0092 per audio minute input
836.36 neurons per audio minute input
@cf/pipecat-ai/smart-turn-v2	$0.00033795 per audio minute input
0.51 neurons per audio minute input
@cf/deepgram/aura-2-en	$0.030 per 1k characters input
2727.27 neurons per 1k characters input
@cf/deepgram/aura-2-es	$0.030 per 1k characters input
2727.27 neurons per 1k characters input
@cf/deepgram/flux (WebSocket)	$0.0077 per audio minute
700.00 neurons per audio minute
Other model pricing
Model	Price in Tokens	Price in Neurons
@cf/huggingface/distilbert-sst-2-int8	$0.026 per M input tokens	2394 neurons per M input tokens
@cf/baai/bge-reranker-base	$0.003 per M input tokens	283 neurons per M input tokens
@cf/meta/m2m100-1.2b	$0.342 per M input tokens
$0.342 per M output tokens	31050 neurons per M input tokens
31050 neurons per M output tokens
@cf/microsoft/resnet-50	$2.51 per M images	228055 neurons per M images
@cf/ai4bharat/indictrans2-en-indic-1B	$0.342 per M input tokens
$0.342 per M output tokens	31050 neurons per M input tokens
31050 neurons per M output tokens
