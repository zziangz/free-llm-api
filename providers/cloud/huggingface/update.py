#!/usr/bin/env python3
"""
HuggingFace Inference Router Model Registry Updater

This script generates the config.yaml registry file by:
1. Fetching model data from HuggingFace Router /v1/models API
2. Extracting capabilities from each model's providers
3. Generating a unified config with provider routing info

Usage:
    ./update.py                    # Generate config.yaml from cached models.json
    ./update.py --fetch            # Fetch latest from HuggingFace API first
    ./update.py --validate         # Validate generated YAML

See README.md for maintenance workflow.
"""
import json
import yaml
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


def load_dotenv():
    """Load environment variables from .env file in project root"""
    current = Path(__file__).parent
    for _ in range(5):
        env_file = current / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = value
            return
        current = current.parent

load_dotenv()


# Free providers that we have separate configs for
FREE_PROVIDERS = {'cerebras', 'groq', 'sambanova', 'hyperbolic', 'hf-inference'}


def load_metadata() -> Dict:
    """Load curated model metadata"""
    try:
        with open('metadata.yaml', 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print("Warning: metadata.yaml not found, using heuristics only")
        return {}


def fetch_models() -> List[Dict]:
    """Fetch latest models from HuggingFace Router API"""
    api_key = os.environ.get('HF_TOKEN')
    if not api_key:
        print("Error: HF_TOKEN environment variable not set")
        sys.exit(1)
    
    print("Fetching models from HuggingFace Router API...")
    
    # Use curl since requests may have SSL issues
    cmd = [
        'curl', '-s',
        'https://router.huggingface.co/v1/models',
        '-H', f'Authorization: Bearer {api_key}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    models = data.get('data', [])
    print(f"✓ Found {len(models)} models")
    return models


def load_cached_models() -> List[Dict]:
    """Load models from cached models.json"""
    try:
        with open('models.json', 'r') as f:
            data = json.load(f)
            # Handle both raw list and {data: [...]} format
            if isinstance(data, list):
                return data
            return data.get('data', data)
    except FileNotFoundError:
        print("Error: models.json not found. Run with --fetch to get latest data.")
        sys.exit(1)


def save_models_cache(models: List[Dict]):
    """Save models to cache file"""
    with open('models.json', 'w') as f:
        json.dump({'data': models}, f, indent=2)
    print(f"✓ Saved {len(models)} models to models.json")


def get_best_provider(providers: List[Dict]) -> Optional[Dict]:
    """Get the best provider for a model, preferring free providers"""
    if not providers:
        return None
    
    # First try free providers
    for p in providers:
        if p.get('provider') in FREE_PROVIDERS and p.get('status') == 'live':
            return p
    
    # Then any live provider
    for p in providers:
        if p.get('status') == 'live':
            return p
    
    return providers[0]


def generate_config(models: List[Dict], metadata: Dict) -> Dict:
    """Generate the config.yaml structure"""
    
    defaults = metadata.get('defaults', {})
    default_context = defaults.get('contextWindow', 32768)
    default_max_output = defaults.get('maxOutputTokens', 4096)
    
    config = {
        '$id': 'huggingface',
        'name': 'HuggingFace Inference Router',
        'description': 'Unified gateway to 15+ inference providers through HuggingFace Hub',
        'url': 'https://huggingface.co',
        'docs': 'https://huggingface.co/docs/api-inference/index',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'HuggingFace Token',
            'keyUrl': 'https://huggingface.co/settings/tokens',
        },
        'endpoint': {
            'baseUrl': 'https://router.huggingface.co/v1',
            'protocol': 'openai',
        },
        'limits': {
            'credits': {
                'monthly': 0.10,
                'description': 'Free tier: $0.10/month credits, then pay-as-you-go'
            }
        },
        'providers': sorted(list({
            p.get('provider')
            for m in models
            for p in m.get('providers', [])
            if p.get('provider')
        })),
        'models': []
    }
    
    processed_ids = set()
    
    for model in models:
        model_id = model.get('id', '')
        
        # Skip duplicates
        if model_id in processed_ids:
            continue
        processed_ids.add(model_id)
        
        # Get architecture info
        arch = model.get('architecture', {})
        input_modalities = arch.get('input_modalities', ['text'])
        output_modalities = arch.get('output_modalities', ['text'])
        
        # Determine modalities for our schema
        modalities = ['text-to-text']
        if 'image' in input_modalities:
            modalities.append('image-to-text')
        if 'audio' in input_modalities:
            modalities.append('audio-to-text')
        
        # Get best provider info
        providers = model.get('providers', [])
        best_provider = get_best_provider(providers)
        
        if not best_provider:
            continue
        
        # Get capabilities from best provider
        context_window = best_provider.get('context_length') or default_context
        has_tools = best_provider.get('supports_tools', False)
        has_structured = best_provider.get('supports_structured_output', False)
        has_vision = 'image' in input_modalities
        
        # Check if any free provider is available
        free_providers = [
            p.get('provider') for p in providers 
            if p.get('provider') in FREE_PROVIDERS and p.get('status') == 'live'
        ]
        is_free = len(free_providers) > 0
        
        # Get all available providers
        available_providers = [
            p.get('provider') for p in providers if p.get('status') == 'live'
        ]
        
        model_entry = {
            'id': model_id,
            'upstream': model_id,
            'free': is_free,
            'modalities': modalities,
            'contextWindow': context_window,
            'maxOutputTokens': default_max_output,
            'capabilities': {
                'streaming': True,
                'tools': has_tools,
                'vision': has_vision,
                'json': has_structured or has_tools
            },
            'providers': available_providers
        }
        
        # Add free providers note if applicable
        if free_providers:
            model_entry['freeVia'] = free_providers
        
        config['models'].append(model_entry)
    
    # Sort models by id
    config['models'].sort(key=lambda x: x['id'])
    
    return config


def write_config(config: Dict):
    """Write config to YAML file with nice formatting"""
    output_path = 'config.yaml'
    
    with open(output_path, 'w') as f:
        # Write header
        f.write(f'$id: "{config["$id"]}"\n')
        f.write(f'name: "{config["name"]}"\n')
        f.write(f'description: "{config["description"]}"\n')
        f.write(f'url: "{config["url"]}"\n')
        f.write(f'docs: "{config["docs"]}"\n\n')
        
        # Auth section
        f.write('auth:\n')
        f.write(f'  type: "{config["auth"]["type"]}"\n')
        f.write(f'  keyLabel: "{config["auth"]["keyLabel"]}"\n')
        f.write(f'  keyUrl: "{config["auth"]["keyUrl"]}"\n\n')
        
        # Endpoint section
        f.write('# HuggingFace Router is OpenAI-compatible\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n\n')
        
        # Limits section
        f.write('# Free tier is very limited - $0.10/month\n')
        f.write('# Consider using dedicated free providers (Cerebras, Groq, etc.)\n')
        f.write('limits:\n')
        f.write('  credits:\n')
        f.write(f'    monthly: {config["limits"]["credits"]["monthly"]}\n')
        f.write(f'    description: "{config["limits"]["credits"]["description"]}"\n\n')
        
        # Providers list
        f.write('# Available inference providers through this router\n')
        f.write('providers:\n')
        for provider in config['providers']:
            f.write(f'  - {provider}\n')
        f.write('\n')
        
        # Models section
        f.write('models:\n')
        for model in config['models']:
            f.write(f'  - id: "{model["id"]}"\n')
            f.write(f'    upstream: "{model["upstream"]}"\n')
            f.write(f'    free: {str(model["free"]).lower()}\n')
            f.write('    modalities:\n')
            for modality in model['modalities']:
                f.write(f'      - {modality}\n')
            f.write(f'    contextWindow: {model["contextWindow"]}\n')
            f.write(f'    maxOutputTokens: {model["maxOutputTokens"]}\n')
            f.write('    capabilities:\n')
            f.write(f'      streaming: {str(model["capabilities"]["streaming"]).lower()}\n')
            f.write(f'      tools: {str(model["capabilities"]["tools"]).lower()}\n')
            f.write(f'      vision: {str(model["capabilities"]["vision"]).lower()}\n')
            f.write(f'      json: {str(model["capabilities"]["json"]).lower()}\n')
            f.write('    providers:\n')
            for p in model['providers']:
                f.write(f'      - {p}\n')
            if model.get('freeVia'):
                f.write('    freeVia:\n')
                for p in model['freeVia']:
                    f.write(f'      - {p}\n')
            f.write('\n')
        
        # Footer
        f.write('status: "active"\n')
        f.write('env: "HF_TOKEN"\n')
        f.write('tags:\n')
        f.write('  - aggregator\n')
        f.write('  - openai-compatible\n')
        f.write('  - multi-provider\n')
        f.write('  - credit-limited\n')
    
    # Print summary
    print(f"✓ Generated {output_path} with {len(config['models'])} models")
    
    vision_count = sum(1 for m in config['models'] if m['capabilities']['vision'])
    tools_count = sum(1 for m in config['models'] if m['capabilities']['tools'])
    free_count = sum(1 for m in config['models'] if m['free'])
    provider_count = len(config['providers'])
    
    print(f"  - Vision models: {vision_count}")
    print(f"  - Models with tools: {tools_count}")
    print(f"  - Free-routed models: {free_count}")
    print(f"  - Backend providers: {provider_count}")


def validate_output() -> bool:
    """Basic validation of generated YAML"""
    output_path = 'config.yaml'
    try:
        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check required fields
        required = ['$id', 'name', 'description', 'auth', 'endpoint', 'models']
        missing = [field for field in required if field not in data]
        
        if missing:
            print(f"\n✗ Missing required fields: {missing}")
            return False
        
        print(f"\n✓ YAML is valid")
        print(f"  Provider: {data.get('name')}")
        print(f"  Models: {len(data.get('models', []))}")
        print(f"  Status: {data.get('status')}")
        return True
    except Exception as e:
        print(f"\n✗ YAML validation failed: {e}")
        return False


def main():
    args = sys.argv[1:]
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Load metadata
    metadata = load_metadata()
    
    # Fetch if requested
    if '--fetch' in args:
        models = fetch_models()
        save_models_cache(models)
    else:
        models = load_cached_models()
    
    # Generate config
    config = generate_config(models, metadata)
    write_config(config)
    
    # Validate if requested
    if '--validate' in args:
        if not validate_output():
            sys.exit(1)


if __name__ == '__main__':
    main()
