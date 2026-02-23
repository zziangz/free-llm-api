#!/usr/bin/env python3
"""
Cerebras Model Registry Updater

Generates config.yaml by combining:
1. Model data from Cerebras /v1/models API
2. Curated metadata from metadata.yaml

Usage:
    ./update.py                    # Generate from cached models.json
    ./update.py --fetch            # Fetch latest from API first
    ./update.py --validate         # Validate generated YAML
"""
import json
import yaml
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List


def load_dotenv():
    """Load environment variables from .env file"""
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
        return {}


def fetch_models() -> List[Dict]:
    """Fetch latest models from Cerebras API"""
    # Try both spellings of the env var
    api_key = os.environ.get('CEREBRAS_API_KEY') or os.environ.get('CEREBAS_API_KEY')
    if not api_key:
        print("Error: CEREBRAS_API_KEY not set")
        sys.exit(1)
    
    print("Fetching models from Cerebras API...")
    cmd = [
        'curl', '-s',
        'https://api.cerebras.ai/v1/models',
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
            if isinstance(data, list):
                return data
            return data.get('data', data)
    except FileNotFoundError:
        print("Error: models.json not found. Run with --fetch first.")
        sys.exit(1)


def save_models_cache(models: List[Dict]):
    """Save models to cache file"""
    with open('models.json', 'w') as f:
        json.dump({'data': models}, f, indent=2)
    print(f"✓ Saved {len(models)} models to models.json")


def generate_config(models: List[Dict], metadata: Dict) -> Dict:
    """Generate the config.yaml structure"""
    
    function_calling = set(metadata.get('function_calling_models', []))
    json_mode = set(metadata.get('json_mode_models', []))
    vision_models = set(metadata.get('vision_models', []))
    free_models = set(metadata.get('free_models', []))
    context_windows = metadata.get('context_windows', {})
    max_output_tokens = metadata.get('max_output_tokens', {})
    limits = metadata.get('limits', {})
    defaults = metadata.get('defaults', {})
    
    config = {
        '$id': 'cerebras',
        'name': 'Cerebras',
        'description': 'Ultra-fast inference with Wafer Scale Engine technology',
        'url': 'https://cerebras.ai',
        'docs': 'https://cloud.cerebras.ai/platform/docs',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'Cerebras API Key',
            'keyUrl': 'https://cloud.cerebras.ai/platform/',
            'keyPrefix': 'csk-'
        },
        'endpoint': {
            'baseUrl': 'https://api.cerebras.ai/v1',
            'protocol': 'openai'
        },
        'limits': {
            'requests': limits.get('requests', {'perMinute': 30}),
            'tokens': limits.get('tokens', {'perMinute': 60000})
        },
        'models': []
    }
    
    for model in models:
        model_id = model.get('id', '')
        
        context_window = context_windows.get(model_id, defaults.get('contextWindow', 65536))
        max_output = max_output_tokens.get(model_id, defaults.get('maxOutputTokens', 8192))
        
        modalities = ['text-to-text']
        if model_id in vision_models:
            modalities.append('image-to-text')
        
        has_tools = model_id in function_calling or len(function_calling) == 0
        has_json = model_id in json_mode or len(json_mode) == 0
        has_vision = model_id in vision_models
        is_free = model_id in free_models or len(free_models) == 0
        
        model_entry = {
            'id': model_id,
            'upstream': model_id,
            'free': is_free,
            'modalities': modalities,
            'contextWindow': context_window,
            'maxOutputTokens': max_output,
            'capabilities': {
                'streaming': True,
                'tools': has_tools,
                'vision': has_vision,
                'json': has_json
            }
        }
        
        config['models'].append(model_entry)
    
    config['models'].sort(key=lambda x: x['id'])
    
    return config


def write_config(config: Dict):
    """Write config to YAML file"""
    output_path = 'config.yaml'
    
    with open(output_path, 'w') as f:
        f.write(f'$id: "{config["$id"]}"\n')
        f.write(f'name: "{config["name"]}"\n')
        f.write(f'description: "{config["description"]}"\n')
        f.write(f'url: "{config["url"]}"\n')
        f.write(f'docs: "{config["docs"]}"\n\n')
        
        f.write('auth:\n')
        f.write(f'  type: "{config["auth"]["type"]}"\n')
        f.write(f'  keyLabel: "{config["auth"]["keyLabel"]}"\n')
        f.write(f'  keyUrl: "{config["auth"]["keyUrl"]}"\n')
        f.write(f'  keyPrefix: "{config["auth"]["keyPrefix"]}"\n\n')
        
        f.write('# Cerebras uses OpenAI-compatible API\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n\n')
        
        f.write('# Free tier rate limits\n')
        f.write('limits:\n')
        f.write('  requests:\n')
        for k, v in config['limits']['requests'].items():
            f.write(f'    {k}: {v}\n')
        f.write('  tokens:\n')
        for k, v in config['limits']['tokens'].items():
            f.write(f'    {k}: {v}\n')
        f.write('\n')
        
        f.write('models:\n')
        for model in config['models']:
            f.write(f'  - id: "{model["id"]}"\n')
            f.write(f'    upstream: "{model["upstream"]}"\n')
            f.write(f'    free: {str(model["free"]).lower()}\n')
            f.write('    modalities:\n')
            for m in model['modalities']:
                f.write(f'      - {m}\n')
            f.write(f'    contextWindow: {model["contextWindow"]}\n')
            f.write(f'    maxOutputTokens: {model["maxOutputTokens"]}\n')
            f.write('    capabilities:\n')
            f.write(f'      streaming: {str(model["capabilities"]["streaming"]).lower()}\n')
            f.write(f'      tools: {str(model["capabilities"]["tools"]).lower()}\n')
            f.write(f'      vision: {str(model["capabilities"]["vision"]).lower()}\n')
            f.write(f'      json: {str(model["capabilities"]["json"]).lower()}\n')
            f.write('\n')
        
        f.write('status: "active"\n')
        f.write('env: "CEREBRAS_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - fast\n')
        f.write('  - openai-compatible\n')
    
    print(f"✓ Generated {output_path} with {len(config['models'])} models")


def validate_output() -> bool:
    """Validate generated YAML"""
    try:
        with open('config.yaml', 'r') as f:
            data = yaml.safe_load(f)
        
        required = ['$id', 'name', 'auth', 'endpoint', 'models']
        missing = [f for f in required if f not in data]
        
        if missing:
            print(f"✗ Missing fields: {missing}")
            return False
        
        print(f"✓ YAML valid - {len(data.get('models', []))} models")
        return True
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False


def main():
    args = sys.argv[1:]
    os.chdir(Path(__file__).parent)
    
    metadata = load_metadata()
    
    if '--fetch' in args:
        models = fetch_models()
        save_models_cache(models)
    else:
        models = load_cached_models()
    
    config = generate_config(models, metadata)
    write_config(config)
    
    if '--validate' in args:
        if not validate_output():
            sys.exit(1)


if __name__ == '__main__':
    main()
