#!/usr/bin/env python3
"""
Mistral AI Model Registry Updater

This script generates the config.yaml registry file by combining:
1. Model data from Mistral /v1/models API (cached in models.json)
2. Curated metadata from metadata.yaml (manually maintained)
3. Intelligent heuristics for unknown models

Usage:
    ./update.py                    # Generate config.yaml from cached models.json
    ./update.py --fetch            # Fetch latest from Mistral API first
    ./update.py --validate         # Validate generated YAML

See README.md for maintenance workflow.
"""
import json
import yaml
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


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


def load_metadata() -> Dict:
    """Load curated model metadata"""
    try:
        with open('metadata.yaml', 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print("Warning: metadata.yaml not found, using heuristics only")
        return {}


def fetch_models() -> List[Dict]:
    """Fetch latest models from Mistral API"""
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        print("Error: MISTRAL_API_KEY environment variable not set")
        sys.exit(1)
    
    print("Fetching models from Mistral API...")
    
    try:
        import requests
        response = requests.get(
            'https://api.mistral.ai/v1/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
    except ImportError:
        # Fallback to curl
        cmd = [
            'curl', '-s',
            'https://api.mistral.ai/v1/models',
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


def generate_config(models: List[Dict], metadata: Dict) -> Dict:
    """Generate the config.yaml structure"""
    
    vision_models = set(metadata.get('vision_models', []))
    function_calling = set(metadata.get('function_calling_models', []))
    fim_models = set(metadata.get('fim_models', []))
    context_windows = metadata.get('context_windows', {})
    free_models = set(metadata.get('free_models', []))
    json_mode = set(metadata.get('json_mode_models', []))
    max_output = metadata.get('max_output_tokens', {})
    deprecated = set(metadata.get('deprecated_models', []))
    embedding_models = set(metadata.get('embedding_models', []))
    moderation_models = set(metadata.get('moderation_models', []))
    defaults = metadata.get('defaults', {})
    
    default_context = defaults.get('contextWindow', 32768)
    default_max_output = defaults.get('maxOutputTokens', 8192)
    
    config = {
        '$id': 'mistral',
        'name': 'Mistral AI',
        'description': 'Mistral AI - Open-source and proprietary frontier models from France',
        'url': 'https://mistral.ai',
        'docs': 'https://docs.mistral.ai',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'Mistral API Key',
            'keyUrl': 'https://console.mistral.ai/api-keys',
        },
        'endpoint': {
            'baseUrl': 'https://api.mistral.ai/v1',
            'protocol': 'openai',  # Mistral is OpenAI-compatible!
        },
        'limits': {
            'requests': {
                'perMinute': 1,  # Free tier
                'description': 'Free tier: 1 req/min, 500K tokens/min, 1B tokens/month'
            },
            'tokens': {
                'perMinute': 500000,
                'perMonth': 1000000000
            }
        },
        'models': []
    }
    
    processed_ids = set()
    
    for model in models:
        model_id = model.get('id', '')
        
        # Skip duplicates
        if model_id in processed_ids:
            continue
        processed_ids.add(model_id)
        
        # Skip deprecated models
        if model_id in deprecated:
            continue
        
        # Skip embedding models (different modality)
        if model_id in embedding_models:
            continue
        
        # Skip moderation models
        if model_id in moderation_models:
            continue
        
        # Skip fine-tuned models (ft: prefix)
        if model_id.startswith('ft:'):
            continue
        
        # Get capabilities from API response
        caps = model.get('capabilities', {})
        has_chat = caps.get('completion_chat', True)
        has_tools = caps.get('function_calling', False) or model_id in function_calling
        has_vision = caps.get('vision', False) or model_id in vision_models
        has_fim = caps.get('completion_fim', False) or model_id in fim_models
        
        # Skip non-chat models
        if not has_chat and not has_fim:
            continue
        
        # Determine modalities
        modalities = ['text-to-text']
        if has_vision:
            modalities.append('image-to-text')
        
        # Get context window from API or metadata
        context_window = model.get('max_context_length') or context_windows.get(model_id, default_context)
        
        # Is this a free tier model?
        is_free = model_id in free_models or '-latest' in model_id
        
        # Get max output tokens
        model_max_output = max_output.get(model_id, default_max_output)
        
        # Has JSON mode?
        has_json = model_id in json_mode or has_tools
        
        model_entry = {
            'id': model_id,
            'upstream': model_id,
            'free': is_free,
            'modalities': modalities,
            'contextWindow': context_window,
            'maxOutputTokens': model_max_output,
            'capabilities': {
                'streaming': True,  # All Mistral models support streaming
                'tools': has_tools,
                'vision': has_vision,
                'json': has_json
            }
        }
        
        # Add FIM capability note
        if has_fim:
            model_entry['capabilities']['fim'] = True
        
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
        f.write('# Mistral API is OpenAI-compatible - can use OpenAI SDK directly\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n\n')
        
        # Limits section
        f.write('# Free tier rate limits\n')
        f.write('limits:\n')
        f.write('  requests:\n')
        f.write(f'    perMinute: {config["limits"]["requests"]["perMinute"]}\n')
        f.write(f'    description: "{config["limits"]["requests"]["description"]}"\n')
        f.write('  tokens:\n')
        f.write(f'    perMinute: {config["limits"]["tokens"]["perMinute"]}\n')
        f.write(f'    perMonth: {config["limits"]["tokens"]["perMonth"]}\n\n')
        
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
            if model['capabilities'].get('fim'):
                f.write('      fim: true\n')
            f.write('\n')
        
        # Footer
        f.write('status: "active"\n')
        f.write('env: "MISTRAL_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - openai-compatible\n')
        f.write('  - rate-limited\n')
    
    # Print summary
    print(f"✓ Generated {output_path} with {len(config['models'])} models")
    
    vision_count = sum(1 for m in config['models'] if m['capabilities']['vision'])
    tools_count = sum(1 for m in config['models'] if m['capabilities']['tools'])
    free_count = sum(1 for m in config['models'] if m['free'])
    fim_count = sum(1 for m in config['models'] if m['capabilities'].get('fim'))
    
    print(f"  - Vision models: {vision_count}")
    print(f"  - Models with tools: {tools_count}")
    print(f"  - Free tier models: {free_count}")
    print(f"  - FIM (code) models: {fim_count}")


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


def create_sample_models() -> List[Dict]:
    """Create a sample models list when API fetch not available"""
    return [
        # Premier models
        {
            "id": "mistral-large-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": False},
            "max_context_length": 131072
        },
        {
            "id": "mistral-large-2411",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": False},
            "max_context_length": 131072
        },
        
        # Small models
        {
            "id": "mistral-small-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": True},
            "max_context_length": 32768
        },
        {
            "id": "mistral-small-2501",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": True},
            "max_context_length": 32768
        },
        
        # Ministral (edge)
        {
            "id": "ministral-3b-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": False},
            "max_context_length": 131072
        },
        {
            "id": "ministral-8b-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": False},
            "max_context_length": 131072
        },
        
        # Code models
        {
            "id": "codestral-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "completion_fim": True, "vision": False},
            "max_context_length": 32768
        },
        
        # Vision models
        {
            "id": "pixtral-12b-latest",
            "capabilities": {"completion_chat": True, "function_calling": False, "vision": True},
            "max_context_length": 131072
        },
        {
            "id": "pixtral-large-latest",
            "capabilities": {"completion_chat": True, "function_calling": True, "vision": True},
            "max_context_length": 131072
        },
    ]


def main():
    args = sys.argv[1:]
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Load metadata
    metadata = load_metadata()
    
    # Fetch if requested
    if '--fetch' in args:
        api_key = os.environ.get('MISTRAL_API_KEY')
        if api_key:
            models = fetch_models()
            save_models_cache(models)
        else:
            print("Warning: MISTRAL_API_KEY not set, using sample models")
            models = create_sample_models()
            save_models_cache(models)
    else:
        # Try to load cached models
        try:
            models = load_cached_models()
        except SystemExit:
            print("Creating initial models.json from sample list...")
            models = create_sample_models()
            save_models_cache(models)
    
    # Generate config
    config = generate_config(models, metadata)
    write_config(config)
    
    # Validate if requested
    if '--validate' in args:
        if not validate_output():
            sys.exit(1)


if __name__ == '__main__':
    main()
