#!/usr/bin/env python3
"""
Google Gemini/AI Studio Model Registry Updater

Generates config.yaml by:
1. Fetching models from Gemini /v1beta/models API
2. Filtering to chat-capable models
3. Applying curated metadata

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
from typing import Dict, List, Set


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
    """Fetch latest models from Gemini API"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)
    
    print("Fetching models from Gemini API...")
    cmd = [
        'curl', '-s',
        f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    models = data.get('models', [])
    print(f"✓ Found {len(models)} total models")
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
    function_calling = set(metadata.get('function_calling_models', []))
    thinking_models = set(metadata.get('thinking_models', []))
    json_mode = set(metadata.get('json_mode_models', []))
    tts_models = set(metadata.get('tts_models', []))
    image_gen_models = set(metadata.get('image_gen_models', []))
    embedding_models = set(metadata.get('embedding_models', []))
    free_models = set(metadata.get('free_models', []))
    limits = metadata.get('limits', {})
    defaults = metadata.get('defaults', {})
    
    config = {
        '$id': 'gemini',
        'name': 'Google AI Studio (Gemini)',
        'description': 'Google\'s Gemini models with massive context windows and multimodal support',
        'url': 'https://aistudio.google.com',
        'docs': 'https://ai.google.dev/docs',
        'auth': {
            'type': 'query',
            'keyLabel': 'Google AI API Key',
            'keyUrl': 'https://aistudio.google.com/api-keys',
            'keyParam': 'key'
        },
        'endpoint': {
            'baseUrl': 'https://generativelanguage.googleapis.com/v1beta',
            'protocol': 'gemini'  # Custom protocol, not OpenAI
        },
        'limits': {
            'requests': limits.get('requests', {'perMinute': 15}),
            'tokens': limits.get('tokens', {'perMinute': 1000000})
        },
        'models': []
    }
    
    for model in models:
        model_name = model.get('name', '').replace('models/', '')
        methods = model.get('supportedGenerationMethods', [])
        
        # Skip non-chat models
        if 'generateContent' not in methods:
            continue
        
        # Skip embedding models
        if model_name in embedding_models or 'embedding' in model_name.lower():
            continue
        
        # Skip models without free tier quota
        if free_models and model_name not in free_models:
            continue
        
        # Skip TTS models (different capability)
        if model_name in tts_models or '-tts' in model_name:
            continue
        
        # Skip image generation experiments
        if model_name in image_gen_models or 'image-generation' in model_name:
            continue
        
        input_tokens = model.get('inputTokenLimit', defaults.get('contextWindow', 1048576))
        output_tokens = model.get('outputTokenLimit', defaults.get('maxOutputTokens', 8192))
        has_thinking = model.get('thinking', False) or model_name in thinking_models
        
        # Determine modalities (all Gemini models are multimodal)
        modalities = ['text-to-text']
        if model_name in vision_models or model_name.startswith('gemini-'):
            modalities.append('image-to-text')
        
        has_tools = model_name in function_calling
        has_json = model_name in json_mode
        has_vision = 'image-to-text' in modalities
        is_free = model_name in free_models or len(free_models) == 0
        
        model_entry = {
            'id': model_name,
            'upstream': model_name,
            'free': is_free,
            'modalities': modalities,
            'contextWindow': input_tokens,
            'maxOutputTokens': output_tokens,
            'capabilities': {
                'streaming': True,
                'tools': has_tools,
                'vision': has_vision,
                'json': has_json
            }
        }
        
        if has_thinking:
            model_entry['capabilities']['thinking'] = True
        
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
        f.write(f'  keyParam: "{config["auth"]["keyParam"]}"\n\n')
        
        f.write('# Gemini uses custom protocol (NOT OpenAI-compatible)\n')
        f.write('# Use adapter.py for OpenAI compatibility or Google\'s SDK\n')
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
            if model['capabilities'].get('thinking'):
                f.write('      thinking: true\n')
            f.write('\n')
        
        f.write('status: "active"\n')
        f.write('env: "GEMINI_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - rate-limited\n')
        f.write('  - multimodal\n')
        f.write('  - large-context\n')
    
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
