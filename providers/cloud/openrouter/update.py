#!/usr/bin/env python3
"""
OpenRouter Model Registry Updater

Generates config.yaml by:
1. Fetching models from OpenRouter /api/v1/models API
2. Filtering to only include free models (":free" suffix)
3. Extracting capabilities from API response

Usage:
    ./update.py                    # Generate from cached models.json
    ./update.py --fetch            # Fetch latest from API first
    ./update.py --validate         # Validate generated YAML
    ./update.py --all              # Include all models, not just free
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
    """Fetch latest models from OpenRouter API"""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)
    
    print("Fetching models from OpenRouter API...")
    cmd = [
        'curl', '-s',
        'https://openrouter.ai/api/v1/models',
        '-H', f'Authorization: Bearer {api_key}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    models = data.get('data', [])
    print(f"✓ Found {len(models)} total models")
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


def generate_config(models: List[Dict], metadata: Dict, include_all: bool = False) -> Dict:
    """Generate the config.yaml structure"""
    
    vision_models = set(metadata.get('vision_models', []))
    deprecated = set(metadata.get('deprecated_models', []))
    limits = metadata.get('limits', {})
    defaults = metadata.get('defaults', {})
    
    config = {
        '$id': 'openrouter',
        'name': 'OpenRouter',
        'description': 'Model aggregator with access to 300+ AI models, including free tier options',
        'url': 'https://openrouter.ai',
        'docs': 'https://openrouter.ai/docs',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'OpenRouter API Key',
            'keyUrl': 'https://openrouter.ai/settings/keys',
            'keyPrefix': 'sk-or-v1-'
        },
        'endpoint': {
            'baseUrl': 'https://openrouter.ai/api/v1',
            'protocol': 'openai'
        },
        'limits': {
            'requests': limits.get('requests', {'perMinute': 20}),
        },
        'models': []
    }
    
    for model in models:
        model_id = model.get('id', '')
        
        # Skip deprecated
        if model_id in deprecated:
            continue
        
        # Filter for free models only (unless --all)
        is_free = ':free' in model_id
        if not include_all and not is_free:
            continue
        
        # Get architecture info
        arch = model.get('architecture', {})
        input_modalities = arch.get('input_modalities', ['text'])
        output_modalities = arch.get('output_modalities', ['text'])
        
        # Determine modalities
        modalities = ['text-to-text']
        if 'image' in input_modalities:
            modalities.append('image-to-text')
        if 'audio' in input_modalities:
            modalities.append('audio-to-text')
        if 'video' in input_modalities:
            modalities.append('video-to-text')
        
        # Get capabilities from supported_parameters
        supported = model.get('supported_parameters', [])
        has_tools = 'tools' in supported or 'tool_choice' in supported
        has_json = 'response_format' in supported or 'structured_outputs' in supported
        has_vision = 'image' in input_modalities or model_id in vision_models
        
        # Get context and limits
        context_window = model.get('context_length') or defaults.get('contextWindow', 131072)
        top_provider = model.get('top_provider', {})
        max_output = top_provider.get('max_completion_tokens') or defaults.get('maxOutputTokens', 8192)
        
        # Clean ID for local reference (remove :free suffix)
        local_id = model_id.replace(':free', '').replace('/', '-')
        
        model_entry = {
            'id': local_id,
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
        
        f.write('# OpenRouter uses OpenAI-compatible API\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n\n')
        
        f.write('# Free tier rate limits\n')
        f.write('limits:\n')
        f.write('  requests:\n')
        for k, v in config['limits']['requests'].items():
            f.write(f'    {k}: {v}\n')
        f.write('\n')
        
        f.write('# Free models only (use --all to include paid)\n')
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
        f.write('env: "OPENROUTER_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - aggregator\n')
        f.write('  - openai-compatible\n')
    
    print(f"✓ Generated {output_path} with {len(config['models'])} models")
    
    vision_count = sum(1 for m in config['models'] if m['capabilities']['vision'])
    tools_count = sum(1 for m in config['models'] if m['capabilities']['tools'])
    free_count = sum(1 for m in config['models'] if m['free'])
    
    print(f"  - Vision models: {vision_count}")
    print(f"  - Models with tools: {tools_count}")
    print(f"  - Free models: {free_count}")


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
    include_all = '--all' in args
    
    if '--fetch' in args:
        models = fetch_models()
        save_models_cache(models)
    else:
        models = load_cached_models()
    
    config = generate_config(models, metadata, include_all)
    write_config(config)
    
    if '--validate' in args:
        if not validate_output():
            sys.exit(1)


if __name__ == '__main__':
    main()
