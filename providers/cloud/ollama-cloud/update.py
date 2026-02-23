#!/usr/bin/env python3
"""
Ollama Cloud Model Registry Updater

Generates config.yaml by:
1. Fetching models from https://ollama.com/api/tags
2. Applying curated metadata

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


def load_metadata() -> Dict:
    """Load curated model metadata"""
    try:
        with open('metadata.yaml', 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def fetch_models() -> List[Dict]:
    """Fetch latest models from Ollama Cloud API"""
    print("Fetching models from Ollama Cloud API...")
    cmd = ['curl', '-s', 'https://ollama.com/api/tags']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    models = data.get('models', [])
    print(f"✓ Found {len(models)} models")
    return models


def load_cached_models() -> List[Dict]:
    """Load models from cached models.json"""
    try:
        with open('models.json', 'r') as f:
            data = json.load(f)
            return data.get('models', data) if isinstance(data, dict) else data
    except FileNotFoundError:
        print("Error: models.json not found. Run with --fetch first.")
        sys.exit(1)


def save_models_cache(models: List[Dict]):
    """Save models to cache file"""
    with open('models.json', 'w') as f:
        json.dump({'models': models}, f, indent=2)
    print(f"✓ Saved {len(models)} models to models.json")


def generate_config(models: List[Dict], metadata: Dict) -> Dict:
    """Generate the config.yaml structure"""
    
    vision_models = set(metadata.get('vision_models', []))
    thinking_models = set(metadata.get('thinking_models', []))
    code_models = set(metadata.get('code_models', []))
    function_calling = set(metadata.get('function_calling_models', []))
    context_windows = metadata.get('context_windows', {})
    defaults = metadata.get('defaults', {})
    limits = metadata.get('limits', {})
    
    config = {
        '$id': 'ollama-cloud',
        'name': 'Ollama Cloud',
        'description': 'Run large open-source models in the cloud via Ollama\'s hosted infrastructure',
        'url': 'https://ollama.com',
        'docs': 'https://docs.ollama.com/cloud',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'Ollama API Key',
            'keyUrl': 'https://ollama.com/settings/keys'
        },
        'endpoint': {
            'baseUrl': 'https://ollama.com/api',
            'protocol': 'ollama'  # Ollama-native protocol
        },
        'limits': {
            'requests': limits.get('requests', {'perMinute': 60}),
            'tokens': limits.get('tokens', {'perMinute': 100000})
        },
        'models': []
    }
    
    for model in models:
        model_name = model.get('name', model.get('model', ''))
        if not model_name:
            continue
        
        context = context_windows.get(model_name, defaults.get('contextWindow', 32768))
        max_output = defaults.get('maxOutputTokens', 8192)
        
        has_vision = model_name in vision_models
        has_thinking = model_name in thinking_models
        has_code = model_name in code_models
        has_tools = model_name in function_calling
        
        modalities = ['text-to-text']
        if has_vision:
            modalities.append('image-to-text')
        
        model_entry = {
            'id': model_name,
            'upstream': model_name,
            'free': True,  # Ollama Cloud models are free
            'modalities': modalities,
            'contextWindow': context,
            'maxOutputTokens': max_output,
            'capabilities': {
                'streaming': True,
                'tools': has_tools,
                'vision': has_vision,
                'json': True  # Ollama supports JSON mode
            }
        }
        
        if has_thinking:
            model_entry['capabilities']['thinking'] = True
        
        if has_code:
            model_entry['tags'] = ['code']
        
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
        f.write(f'  keyUrl: "{config["auth"]["keyUrl"]}"\n\n')
        
        f.write('# Ollama-native protocol (similar to OpenAI but with differences)\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n\n')
        
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
            if model['capabilities'].get('thinking'):
                f.write('      thinking: true\n')
            if model.get('tags'):
                f.write('    tags:\n')
                for tag in model['tags']:
                    f.write(f'      - {tag}\n')
            f.write('\n')
        
        f.write('status: "active"\n')
        f.write('env: "OLLAMA_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - open-source\n')
        f.write('  - cloud\n')
    
    print(f"✓ Generated {output_path} with {len(config['models'])} models")
    
    vision_count = sum(1 for m in config['models'] if m['capabilities']['vision'])
    tools_count = sum(1 for m in config['models'] if m['capabilities']['tools'])
    thinking_count = sum(1 for m in config['models'] if m['capabilities'].get('thinking'))
    
    print(f"  - Vision models: {vision_count}")
    print(f"  - Models with tools: {tools_count}")
    print(f"  - Thinking models: {thinking_count}")


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
