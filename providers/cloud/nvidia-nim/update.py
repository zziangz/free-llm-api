#!/usr/bin/env python3
"""
NVIDIA NIM Model Registry Updater

This script generates the nvidia-nim.yaml registry file by combining:
1. Raw API data from models.json (fetched from NVIDIA API)
2. Curated metadata from metadata.yaml (manually maintained)
3. Intelligent heuristics for unknown models

Usage:
    ./update.py                    # Generate nvidia-nim.yaml
    ./update.py --fetch            # Fetch latest from API first
    ./update.py --validate         # Validate generated YAML

See PLAN.md for maintenance workflow and SUMMARY.md for coverage details.
"""
import json
import yaml
import sys
import os
from pathlib import Path

def load_metadata():
    """Load curated model metadata"""
    try:
        with open('metadata.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Warning: metadata.yaml not found, using heuristics only")
        return {}

def parse_nvidia_models():
    # Read the JSON file
    try:
        with open('models.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: models.json not found. Run with --fetch to get latest data.")
        sys.exit(1)
    
    # Load curated metadata
    metadata = load_metadata()
    vision_models = set(metadata.get('vision_models', []))
    context_windows = metadata.get('context_windows', {})
    no_tools = set(metadata.get('no_tools_models', []))
    use_cases = metadata.get('use_cases', {})
    
    # Build the YAML structure
    nvidia_config = {
        '$id': 'nvidia-nim',
        'name': 'NVIDIA NIM',
        'description': 'NVIDIA Inference Microservices - Self-hosted & cloud models',
        'url': 'https://build.nvidia.com',
        'docs': 'https://docs.api.nvidia.com',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'NVIDIA API Key',
            'keyUrl': 'https://build.nvidia.com/explore/discover',
            'keyPrefix': 'nvapi-'
        },
        'endpoint': {
            'baseUrl': 'https://integrate.api.nvidia.com/v1',
            'protocol': 'openai'
        },
        'limits': {
            'requests': {
                'perMinute': 30,
                'perDay': 1000
            }
        },
        'models': []
    }
    
    # Process each model
    for model in data['data']:
        model_id = model['id']
        
        # Skip duplicate models
        if any(m['id'] == model_id for m in nvidia_config['models']):
            continue
        
        # Skip embedding and parsing models
        if 'embed' in model_id.lower() or model_id in [
            'nvidia/nemoretriever-parse', 
            'nvidia/nemotron-parse',
            'nvidia/streampetr',
            'baai/bge-m3',
            'snowflake/arctic-embed-l',
            'nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1',
            'nvidia/llama-3.2-nemoretriever-300m-embed-v1',
            'nvidia/llama-3.2-nemoretriever-300m-embed-v2',
            'nvidia/llama-3.2-nv-embedqa-1b-v1',
            'nvidia/llama-3.2-nv-embedqa-1b-v2',
            'nvidia/llama-nemotron-embed-vl-1b-v2',
            'nvidia/nv-embed-v1',
            'nvidia/nv-embedcode-7b-v1',
            'nvidia/nv-embedqa-e5-v5',
            'nvidia/nv-embedqa-mistral-7b-v2',
            'nvidia/embed-qa-4',
            'nvidia/nvclip'
        ]:
            continue
        
        # Check if it's a vision model (from metadata or heuristics)
        has_vision = (
            model_id in vision_models or
            any(keyword in model_id.lower() for keyword in ['vision', 'vila', 'neva', 'clip', 'vl', 'multimodal', 'kosmos', 'paligemma', 'deplot'])
        )
        
        # Get context window (from metadata or heuristics)
        if model_id in context_windows:
            context_window = context_windows[model_id]
        elif '128k' in model_id:
            context_window = 128000
        elif '32k' in model_id:
            context_window = 32000
        elif '8k' in model_id:
            context_window = 8000
        elif '4k' in model_id:
            context_window = 4000
        elif '16k' in model_id:
            context_window = 16000
        else:
            context_window = 128000  # default
        
        # Check if tools are disabled (reasoning/vision models)
        tools_disabled = has_vision or model_id in no_tools
        
        # Determine modalities
        modalities = ['text-to-text']
        if has_vision:
            modalities.append('image-to-text')
        
        # Create model entry
        model_entry = {
            'id': model_id,
            'upstream': model_id,
            'free': True,
            'modalities': modalities,
            'contextWindow': context_window,
            'maxOutputTokens': 8192,
            'capabilities': {
                'streaming': True,
                'tools': not tools_disabled,
                'vision': has_vision,
                'json': not tools_disabled  # JSON mode typically requires tool support
            }
        }
        
        # Add use cases if available (as comment in future)
        if model_id in use_cases:
            model_entry['_use_cases'] = use_cases[model_id]
        
        nvidia_config['models'].append(model_entry)
    
    # Sort models by id for better organization
    nvidia_config['models'].sort(key=lambda x: x['id'])
    
    # Write to YAML file (new convention: config.yaml in provider folder)
    output_path = './config.yaml'
    with open(output_path, 'w') as f:
        # Custom YAML dump to control formatting
        f.write(f'$id: "{nvidia_config["$id"]}"\n')
        f.write(f'name: "{nvidia_config["name"]}"\n')
        f.write(f'description: "{nvidia_config["description"]}"\n')
        f.write(f'url: "{nvidia_config["url"]}"\n')
        f.write(f'docs: "{nvidia_config["docs"]}"\n\n')
        
        f.write('auth:\n')
        f.write(f'  type: "{nvidia_config["auth"]["type"]}"\n')
        f.write(f'  keyLabel: "{nvidia_config["auth"]["keyLabel"]}"\n')
        f.write(f'  keyUrl: "{nvidia_config["auth"]["keyUrl"]}"\n')
        f.write(f'  keyPrefix: "{nvidia_config["auth"]["keyPrefix"]}"\n\n')
        
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{nvidia_config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{nvidia_config["endpoint"]["protocol"]}"\n\n')
        
        f.write('# Global limits for all models under this provider\n')
        f.write('limits:\n')
        f.write('  requests:\n')
        f.write(f'    perMinute: {nvidia_config["limits"]["requests"]["perMinute"]}\n')
        f.write(f'    perDay: {nvidia_config["limits"]["requests"]["perDay"]}\n\n')
        
        f.write('models:\n')
        for model in nvidia_config['models']:
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
            
            # Add use cases as comment if available
            if '_use_cases' in model:
                f.write(f'    # Use cases: {", ".join(model["_use_cases"])}\n')
            f.write('\n')
        
        f.write('status: "active"\n')
        f.write('env: "NVIDIA_API_KEY"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - nvidia\n')
    
    print(f"✓ Generated {output_path} with {len(nvidia_config['models'])} models")
    print(f"  - Vision models: {sum(1 for m in nvidia_config['models'] if m['capabilities']['vision'])}")
    print(f"  - Models with tools: {sum(1 for m in nvidia_config['models'] if m['capabilities']['tools'])}")
    print(f"  - Models with use cases: {sum(1 for m in nvidia_config['models'] if '_use_cases' in m)}")
    return nvidia_config

def fetch_models():
    """Fetch latest models from NVIDIA API"""
    import subprocess
    
    api_key = os.environ.get('NVIDIA_API_KEY')
    if not api_key:
        print("Error: NVIDIA_API_KEY environment variable not set")
        sys.exit(1)
    
    print("Fetching latest models from NVIDIA API...")
    cmd = [
        'curl', '-s',
        'https://integrate.api.nvidia.com/v1/models',
        '-H', f'Authorization: Bearer {api_key}'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        with open('models.json', 'w') as f:
            f.write(result.stdout)
        print("✓ Saved to models.json")
    except subprocess.CalledProcessError as e:
        print(f"Error fetching models: {e}")
        sys.exit(1)

def validate_output():
    """Basic validation of generated YAML"""
    output_path = './config.yaml'
    try:
        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)
        
        print(f"\n✓ YAML is valid")
        print(f"  Provider: {data.get('name')}")
        print(f"  Models: {len(data.get('models', []))}")
        print(f"  Status: {data.get('status')}")
        return True
    except Exception as e:
        print(f"\n✗ YAML validation failed: {e}")
        return False

if __name__ == '__main__':
    # Parse command line arguments
    if '--fetch' in sys.argv:
        fetch_models()
    
    # Generate the YAML
    parse_nvidia_models()
    
    # Validate if requested
    if '--validate' in sys.argv:
        if not validate_output():
            sys.exit(1)
