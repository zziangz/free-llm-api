# Provider Folder Structure

This document describes the standardized folder structure for organizing provider discovery and update code.

## Standard Structure

Each provider with custom discovery/update logic should follow this structure:

```
providers/cloud/{provider-name}/
├── config.yaml         # Generated provider configuration
├── README.md           # Provider-specific documentation
├── update.py           # Script to generate config.yaml
├── metadata.yaml       # Curated model capabilities (if needed)
└── models.json         # Raw API response (if available)
```

## File Purposes

### `config.yaml` (Generated)
The output file containing:
- Provider metadata (name, URL, auth)
- Endpoint configuration
- Rate limits
- Model list with capabilities

### `README.md` (Required)
Provider-specific documentation including:
- Quick start guide
- Maintenance workflow
- Model family reference
- Troubleshooting tips

### `update.py` (Required for automated providers)
Python script that:
- Fetches data from provider API (if available)
- Combines API data + curated metadata + heuristics
- Generates the `{provider-name}.yaml` registry file
- Validates output

**Command line interface:**
```bash
./update.py              # Generate config.yaml
./update.py --fetch      # Fetch latest API data first
./update.py --validate   # Validate generated YAML
```

### `metadata.yaml` (Required for curated providers)
Curated model capabilities when API doesn't provide complete metadata:
- Vision/multimodal model lists
- Context window configurations
- Tool/function calling support
- Use cases and categories
- Special notes/warnings

**Example structure:**
```yaml
vision_models:
  - provider/vision-model-1
  - provider/vision-model-2

context_windows:
  provider/model-1: 131072
  provider/model-2: 262000

no_tools_models:
  - provider/reasoning-model

use_cases:
  provider/model-1:
    - conversational-chat
    - tool-calling
    - code-generation
```

### `models.json` (Optional)
Raw API response from provider's model listing endpoint:
- Cached to reduce API calls during development
- Auto-updated with `./update.py --fetch`
- Gitignored if it changes frequently

## Provider Categories

### 1. API-First Providers (Ideal)
Providers with complete metadata via API (e.g., OpenRouter)

**Structure:**
```
openrouter/
├── config.yaml        # Generated output
├── README.md
├── update.py          # Fetches from API, maps directly to config
└── models.json        # Cached API response
```

**No metadata.yaml needed** - all info comes from API

### 2. Curated Providers (NVIDIA NIM pattern)
Providers with minimal API metadata requiring curation

**Structure:**
```
nvidia-nim/
├── config.yaml        # Generated output
├── README.md
├── update.py          # Combines API + metadata + heuristics
├── metadata.yaml      # Curated capabilities
└── models.json        # Raw API response (minimal data)
```

**Hybrid approach** - combines multiple data sources

### 3. Manual Providers
Providers without APIs requiring full manual curation

**Structure:**
```
manual-provider/
├── config.yaml        # Generated output
├── README.md
├── update.py          # Generates from metadata.yaml only
└── metadata.yaml      # Complete model definitions
```

**No API calls** - everything manually maintained

## Example: NVIDIA NIM

Current implementation demonstrates the curated provider pattern:

```bash
cd providers/cloud/nvidia-nim

# Fetch latest model list from API
export NVIDIA_API_KEY="nvapi-..."
./update.py --fetch

# Generate config.yaml combining:
# - API data (model IDs)
# - metadata.yaml (capabilities, context windows, use cases)
# - Heuristics (fallback detection)
./update.py --validate
```

**Output:** `config.yaml` with 120+ models

**Coverage:**
- 17 vision models (from metadata.yaml)
- 120+ context windows (from metadata.yaml)
- 32 use cases (from metadata.yaml)
- 37 no-tool models (from metadata.yaml)

## Creating a New Provider

### Step 1: Determine Provider Type

**Has complete API?** → Use API-First pattern
**Has partial API?** → Use Curated pattern (like NVIDIA NIM)
**No API?** → Use Manual pattern

### Step 2: Create Folder Structure

```bash
mkdir -p providers/cloud/{provider-name}
cd providers/cloud/{provider-name}
```

### Step 3: Create Files

**README.md:**
```markdown
# Provider Name

Quick start, maintenance workflow, model reference
```

**update.py:**
```python
#!/usr/bin/env python3
"""
Provider Name Registry Updater
"""
# Fetch from API
# Load metadata
# Generate YAML
# Validate
```

**metadata.yaml** (if needed):
```yaml
vision_models: []
context_windows: {}
use_cases: {}
```

### Step 4: Implement Update Script

```python
def fetch_models():
    """Fetch from provider API"""
    pass

def load_metadata():
    """Load curated metadata"""
    pass

def generate_registry():
    """Combine data sources and generate YAML"""
    pass

def validate():
    """Validate generated YAML"""
    pass
```

### Step 5: Test

```bash
chmod +x update.py
./update.py --fetch --validate
```

### Step 6: Document

Update provider README.md with:
- Maintenance workflow
- Model family reference
- Known issues/limitations

## Benefits

### Organized Discovery Logic
- Each provider's update code is self-contained
- Easy to find and maintain
- Clear separation between discovery (folder) and registry (YAML)

### Consistent Patterns
- Same structure across all providers
- Familiar workflow for contributors
- Easy to create new providers

### Version Control
- Track metadata changes separately from registry changes
- Document discovery logic with the metadata
- Clear history of curation decisions

### Scalability
- Add new providers without cluttering root
- Independent update schedules
- Provider-specific documentation

## Migration Plan

For existing providers without folders:

1. **Create provider folder:**
   ```bash
   mkdir -p providers/cloud/{provider-name}
   ```

2. **Move/create update logic:**
   ```bash
   mv update_provider.py providers/cloud/{provider-name}/update.py
   ```

3. **Add metadata if needed:**
   ```bash
   # Create metadata.yaml for curated capabilities
   ```

4. **Document:**
   ```bash
   # Create README.md with provider-specific docs
   ```

5. **Test:**
   ```bash
   cd providers/cloud/{provider-name}
   ./update.py --validate
   ```

## Future Enhancements

### Standardized CLI
```bash
# From repository root
./scripts/update-provider nvidia-nim --fetch --validate
./scripts/update-provider openrouter --dry-run
./scripts/update-all-providers
```

### Metadata Validation
```bash
./scripts/validate-metadata providers/cloud/nvidia-nim/metadata.yaml
```

### Coverage Reports
```bash
./scripts/coverage-report nvidia-nim
# Shows: vision models, context windows, use cases, etc.
```

## See Also

- `providers/cloud/nvidia-nim/` - Reference implementation
- `README.md` - Main repository documentation
- `schema.json` - Provider YAML schema
