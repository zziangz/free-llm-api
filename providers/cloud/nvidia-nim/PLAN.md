# NVIDIA NIM Metadata Retrieval Plan

## Overview
This document outlines a reliable approach for maintaining accurate NVIDIA NIM model metadata for the free-llm-api registry.

## Problem
NVIDIA's `/v1/models` API endpoint provides only basic model information:
- `id`: Model identifier
- `object`: Always "model"
- `created`: Unix timestamp
- `owned_by`: Organization name

It does NOT provide:
- Vision/multimodal capabilities
- Context window sizes
- Tool/function calling support
- Use cases
- Modality information

## Solutions

### 1. **Curated Metadata File** (Primary Approach - IMPLEMENTED)
Maintain a `nvidia_metadata.yaml` file with manually verified model capabilities.

**Advantages:**
- Most accurate
- Version controlled
- Easy to update
- No API rate limits or scraping issues

**Process:**
1. Check NVIDIA's documentation at https://build.nvidia.com and https://docs.api.nvidia.com/nim/reference/
2. Update `nvidia_metadata.yaml` with new models or capability changes
3. Run `parse_nvidia_enhanced.py` to regenerate `cloud/nvidia-nim.yaml`

**Metadata Categories:**
- `vision_models`: List of models supporting image-to-text
- `context_windows`: Model-specific context window overrides (default: 128K)
- `no_tools_models`: Reasoning/thinking models without tool support
- `use_cases`: Documented use cases for each model

### 2. **Heuristic Detection** (Fallback)
The parser uses intelligent heuristics for unknown models:

**Vision Detection:**
- Model name contains: `vision`, `vl`, `vila`, `multimodal`, `kosmos`, `paligemma`, `clip`, `neva`

**Context Window Detection:**
- Parse from model name: `128k`, `32k`, `16k`, `8k`, `4k`
- LLaMA 3.x/4.x models: 131,072 tokens
- Qwen models: 262,000 tokens
- Mistral models: 128,000 tokens
- Default: 128,000 tokens

**Tools Disabled:**
- Vision models (typically don't support function calling)
- Models with `thinking` or `reason` in name
- Models in `no_tools_models` list

### 3. **Semi-Automated Updates** (Recommended Workflow)

```bash
# 1. Fetch latest model list from NVIDIA
curl "https://integrate.api.nvidia.com/v1/models" \
  -H "Authorization: Bearer $NVIDIA_API_KEY" > nvidia-nim.json

# 2. Run enhanced parser (uses curated metadata + heuristics)
python3 parse_nvidia_enhanced.py

# 3. Review new models and update nvidia_metadata.yaml
# Compare output to check for new models needing classification

# 4. Re-run parser after metadata updates
python3 parse_nvidia_enhanced.py

# 5. Validate the generated YAML
# Check for errors and test with your application
```

### 4. **Documentation Sources for Manual Verification**

When adding new models to `nvidia_metadata.yaml`, verify capabilities from:

1. **Model Pages:** `https://build.nvidia.com/{org}/{model-name}`
   - Lists modalities, use cases, context windows
   - Shows example API calls

2. **API Reference:** `https://docs.api.nvidia.com/nim/reference/{model-slug}`
   - Details parameters, capabilities
   - Includes use case descriptions

3. **Model Cards:** Check for official model cards on HuggingFace or model provider sites

### 5. **Future Enhancements** (Optional)

If NVIDIA provides better APIs or if we need more automation:

#### A. Web Scraping (Fragile)
```python
# Could parse build.nvidia.com pages
# NOT RECOMMENDED: brittle, requires maintenance
```

#### B. Model Testing
```python
# Send test requests to verify capabilities
# Useful for: tool support, JSON mode
# Cost: API rate limits, requires API key
```

#### C. Community Contributions
- Accept PRs for metadata updates
- Validate against official documentation
- Track metadata version/last-updated dates

## Maintenance Schedule

**Weekly:**
- Fetch latest model list to check for new additions

**Monthly:**
- Review NVIDIA's changelog/release notes
- Update metadata for any capability changes

**As Needed:**
- When users report model issues
- When NVIDIA announces major updates

## File Structure

```
providers/
├── nvidia-nim.json           # Raw API response (fetched via curl)
├── nvidia_metadata.yaml      # Curated metadata (manually maintained)
├── parse_nvidia_enhanced.py  # Enhanced parser (uses metadata + heuristics)
├── parse_nvidia.py           # Basic parser (heuristics only, deprecated)
└── cloud/
    └── nvidia-nim.yaml       # Generated provider config (do not edit directly)
```

## Validation Checklist

When generating `nvidia-nim.yaml`, verify:

- [ ] All vision models have `vision: true` and `modalities: [text-to-text, image-to-text]`
- [ ] Vision/reasoning models have `tools: false` and `json: false`
- [ ] Context windows match official documentation
- [ ] No embedding models included (`embed`, `retriever`, etc.)
- [ ] Model IDs match upstream exactly (case-sensitive)
- [ ] All models have `free: true` (NVIDIA NIM free tier)

## Example: Adding a New Model

```yaml
# nvidia_metadata.yaml

vision_models:
  - new-org/new-vision-model  # Add if it supports image-to-text

context_windows:
  new-org/new-model: 200000   # Add if non-standard context window

use_cases:
  new-org/new-model:
    - conversational-chat
    - tool-calling
    - code-generation
```

Then run:
```bash
python3 parse_nvidia_enhanced.py
```

## Notes

- NVIDIA's model availability changes frequently
- Some models may be deprecated without notice
- Rate limits are subject to change
- Always test critical models in your application
- Keep metadata file in sync with application requirements
