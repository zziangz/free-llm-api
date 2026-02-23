# NVIDIA NIM Provider

Model discovery and registry generation for NVIDIA Inference Microservices.

## Quick Start

```bash
# Update registry from latest NVIDIA API
export NVIDIA_API_KEY="nvapi-..."
./update.py --fetch --validate

# Or manually update if you already have models.json
./update.py
```

## Files

- **`update.py`** - Main script to generate nvidia-nim.yaml
- **`metadata.yaml`** - Curated model capabilities (manually maintained)
- **`models.json`** - Raw API response from NVIDIA (auto-fetched)
- **`../nvidia-nim.yaml`** - Generated registry file (output)
- **`PLAN.md`** - Detailed maintenance workflow
- **`SUMMARY.md`** - Comprehensive metadata coverage reference

## Approach

NVIDIA's `/v1/models` API provides minimal metadata:
```json
{
  "id": "meta/llama-3.3-70b-instruct",
  "object": "model",
  "created": 735790403,
  "owned_by": "meta"
}
```

❌ Missing: capabilities, modalities, context windows, use cases, tool support

### Solution: Curated Metadata + Heuristics

We maintain a comprehensive `metadata.yaml` with:

1. **Vision Models** (17 models)
   - All models supporting image-to-text
   - Example: `meta/llama-3.2-90b-vision-instruct`

2. **Context Windows** (120+ configs)
   - Custom context window for each model family
   - Example: Qwen 3.x → 262K, LLaMA 3.x → 131K

3. **Tool Support** (37 no-tool models)
   - Reasoning/thinking models
   - Vision/multimodal models
   - Guard/safety models

4. **Use Cases** (32 major models)
   - Documented from official NVIDIA pages
   - Example: code-generation, reasoning, multimodal

5. **Model Categories**
   - Code, reasoning, multimodal, long-context, etc.
   - Used for filtering and recommendations

The `update.py` script combines:
- ✅ API data (model IDs)
- ✅ Curated metadata (capabilities)
- ✅ Intelligent heuristics (fallback detection)

## Maintenance Workflow

### Weekly: Check for New Models

```bash
# Fetch latest model list
export NVIDIA_API_KEY="nvapi-..."
./update.py --fetch

# Compare model count
grep -c '"id":' models.json  # New count
grep -c 'id:' ../nvidia-nim.yaml  # Current count
```

### When Adding New Models

1. **Identify new models** from API response
2. **Research capabilities** at https://build.nvidia.com/{org}/{model}
3. **Update `metadata.yaml`:**

   ```yaml
   vision_models:
     - new-org/new-vision-model  # If it supports images
   
   context_windows:
     new-org/new-model: 200000   # If non-standard
   
   use_cases:
     new-org/new-model:
       - conversational-chat
       - tool-calling
   ```

4. **Regenerate registry:**
   ```bash
   ./update.py --validate
   ```

5. **Verify changes:**
   ```bash
   git diff ../nvidia-nim.yaml
   ```

### Monthly: Review Documentation

- Check NVIDIA's changelog for capability updates
- Update context windows if changed
- Add use cases for newly popular models

## Coverage Stats

Current coverage (as of 2026-02-22):

- **167 total models** (100%)
- **17 vision models** with image-to-text
- **130 models** with tool/function calling
- **32 models** with documented use cases
- **120+ custom** context window configurations
- **7 model categories** for organization

## Example: Adding a New Model

When NVIDIA releases `nvidia/nemotron-ultra-253b-v2`:

1. **Fetch latest data:**
   ```bash
   ./update.py --fetch
   ```

2. **Research model at:** https://build.nvidia.com/nvidia/nemotron-ultra-253b-v2
   - Context: 131K tokens
   - Capabilities: Conversational, tool calling, high accuracy
   - Not vision-enabled

3. **Update metadata.yaml:**
   ```yaml
   context_windows:
     nvidia/nemotron-ultra-253b-v2: 131072
   
   use_cases:
     nvidia/nemotron-ultra-253b-v2:
       - conversational-chat
       - tool-calling
       - reasoning
       - high-accuracy
   ```

4. **Generate and validate:**
   ```bash
   ./update.py --validate
   ```

5. **Review output:**
   ```bash
   grep -A 13 "nemotron-ultra-253b-v2" ../nvidia-nim.yaml
   ```

## Model Family Quick Reference

### Meta LLaMA
- LLaMA 3.1: 405B, 70B, 8B (131K context)
- LLaMA 3.2 Vision: 11B, 90B (image support)
- LLaMA 3.3: 70B (131K context)
- LLaMA 4: Maverick & Scout (vision variants)

### NVIDIA Nemotron
- Ultra: 253B (highest accuracy)
- Super: 49B v1.5 (best agentic)
- Standard: 70B, 51B
- Nano: 30B, 12B, 9B, 8B

### Qwen
- Qwen 3.5: 397B multimodal (262K)
- Qwen 3 Coder: 480B (262K)
- QwQ: 32B reasoning

### Microsoft Phi
- Phi-4: Mini, Flash, Multimodal
- Phi-3.5: Vision, MoE, Mini
- Phi-3: Multiple sizes (128K/4K)

### Mistral
- Large 3: 675B (128K)
- Codestral: 22B code gen
- Devstral: 123B software dev
- Mixtral: 8x22B, 8x7B MoE

### DeepSeek
- v3.1/v3.2: General (163K)
- R1 Distill: Reasoning variants
- Coder: Code specialist

## Validation

The `update.py --validate` flag checks:

- ✅ YAML is syntactically valid
- ✅ All vision models have `vision: true`
- ✅ All vision models have `image-to-text` modality
- ✅ No embedding models included
- ✅ Context windows are reasonable (< 2M)

## Troubleshooting

### "models.json not found"
```bash
export NVIDIA_API_KEY="nvapi-..."
./update.py --fetch
```

### "metadata.yaml not found"
Check you're in the `providers/cloud/nvidia-nim/` directory

### Output has fewer models than expected
Check if embedding models are being filtered (expected)

### Context window seems wrong
Update `metadata.yaml` with correct value from docs

## Related Files

- `../../parse_nvidia_enhanced.py` - Legacy parser (deprecated)
- `../../parse_nvidia.py` - Old basic parser (deprecated)
- `../nvidia-nim.yaml` - Final registry file

## Contributing

When submitting updates to metadata.yaml:

1. Include source URLs from build.nvidia.com or docs.api.nvidia.com
2. Test with `./update.py --validate`
3. Check the diff in nvidia-nim.yaml is correct
4. Update SUMMARY.md if adding new categories/features

## License

Part of the free-llm-api registry (MIT License)
