#!/usr/bin/env python3
"""
Cloudflare Workers AI Model Registry Updater

This script generates the config.yaml registry file by combining:
1. Scraped model data from Cloudflare docs (cached in models.json)
2. Curated metadata from metadata.yaml (manually maintained)
3. Intelligent heuristics for unknown models

Usage:
    ./update.py                    # Generate config.yaml from cached models.json
    ./update.py --fetch            # Fetch latest from Cloudflare docs first
    ./update.py --validate         # Validate generated YAML
    ./update.py --fetch --validate # Fetch, generate, and validate

See README.md for maintenance workflow.
"""
import json
import yaml
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Try to import web scraping libraries
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False
    print("Warning: requests/beautifulsoup4 not installed. Run: pip install requests beautifulsoup4")


def load_metadata() -> Dict:
    """Load curated model metadata"""
    try:
        with open('metadata.yaml', 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print("Warning: metadata.yaml not found, using heuristics only")
        return {}


def fetch_models() -> List[Dict]:
    """Fetch latest models from Cloudflare docs by scraping"""
    if not HAS_SCRAPING:
        print("Error: Cannot fetch without requests/beautifulsoup4. Install with:")
        print("  pip install requests beautifulsoup4")
        sys.exit(1)
    
    print("Fetching models from Cloudflare docs...")
    url = "https://developers.cloudflare.com/workers-ai/models/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching models: {e}")
        sys.exit(1)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    models = []
    
    # Find all model links - they follow the pattern /workers-ai/models/{model-name}
    # The page structure has model cards with links containing model info
    model_links = soup.find_all('a', href=re.compile(r'/workers-ai/models/[a-z0-9-]+$'))
    
    seen_models = set()
    
    for link in model_links:
        href = link.get('href', '')
        model_slug = href.split('/')[-1] if href else None
        
        if not model_slug or model_slug in seen_models or model_slug == 'models':
            continue
        
        seen_models.add(model_slug)
        
        # Extract text content from the link and its children
        text_content = link.get_text(separator=' ', strip=True)
        
        # Try to parse task type from text (e.g., "Text Generation • Meta")
        task_type = None
        author = None
        
        # Look for task type patterns
        task_patterns = [
            'Text Generation', 'Text-to-Image', 'Automatic Speech Recognition',
            'Text-to-Speech', 'Text Embeddings', 'Image-to-Text', 'Translation',
            'Text Classification', 'Summarization', 'Object Detection',
            'Image Classification', 'Voice Activity Detection'
        ]
        
        for pattern in task_patterns:
            if pattern in text_content:
                task_type = pattern
                break
        
        # Extract author (usually after task type with •)
        author_match = re.search(r'• (\w+)', text_content)
        if author_match:
            author = author_match.group(1)
        
        # Check for capabilities
        capabilities = []
        if 'Function calling' in text_content:
            capabilities.append('function_calling')
        if 'Batch' in text_content:
            capabilities.append('batch')
        if 'LoRA' in text_content:
            capabilities.append('lora')
        if 'Partner' in text_content:
            capabilities.append('partner')
        if 'Real-time' in text_content:
            capabilities.append('realtime')
        if 'Beta' in text_content:
            capabilities.append('beta')
        if 'Deprecated' in text_content:
            capabilities.append('deprecated')
        
        # Get description - usually the longer text block
        description = None
        desc_parts = text_content.split('•')
        if len(desc_parts) > 1:
            # Look for the longest part that isn't just the model name
            for part in desc_parts:
                part = part.strip()
                if len(part) > 50 and model_slug not in part.lower():
                    description = part
                    break
        
        model_entry = {
            'slug': model_slug,
            'model_id': f"@cf/{model_slug.replace('-', '/', 1)}" if '-' in model_slug else f"@cf/{model_slug}",
            'task_type': task_type or 'Text Generation',  # Default to Text Generation
            'author': author,
            'capabilities': capabilities,
            'description': description
        }
        
        models.append(model_entry)
    
    # If we didn't find many models, try alternative parsing
    if len(models) < 20:
        print(f"Warning: Only found {len(models)} models via links, trying alternative parsing...")
        models = parse_models_alternative(soup, models, seen_models)
    
    print(f"✓ Found {len(models)} models")
    return models


def parse_models_alternative(soup: BeautifulSoup, existing_models: List[Dict], seen: set) -> List[Dict]:
    """Alternative parsing method using different page structure patterns"""
    models = existing_models.copy()
    
    # Try finding model information from any text that looks like a model listing
    # Pattern: model-name followed by task type
    text = soup.get_text()
    
    # Common Cloudflare model prefixes/patterns
    model_patterns = [
        r'(llama-[a-z0-9.-]+(?:-instruct|-chat|-fp8|-awq|-fast)?)',
        r'(gemma-[a-z0-9.-]+(?:-it|-lora)?)',
        r'(mistral-[a-z0-9.-]+(?:-instruct)?)',
        r'(qwen[a-z0-9.-]*)',
        r'(whisper[a-z0-9.-]*)',
        r'(flux-[a-z0-9.-]+)',
        r'(stable-diffusion[a-z0-9.-]*)',
        r'(bge-[a-z0-9.-]+)',
        r'(deepseek-[a-z0-9.-]+)',
    ]
    
    for pattern in model_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            slug = match.lower().replace(' ', '-')
            if slug not in seen and len(slug) > 3:
                seen.add(slug)
                # Infer task type from model name
                task_type = infer_task_type(slug)
                models.append({
                    'slug': slug,
                    'model_id': f"@cf/{slug}",
                    'task_type': task_type,
                    'author': None,
                    'capabilities': [],
                    'description': None
                })
    
    return models


def infer_task_type(model_name: str) -> str:
    """Infer task type from model name"""
    name_lower = model_name.lower()
    
    if any(x in name_lower for x in ['flux', 'stable-diffusion', 'sdxl', 'dreamshaper', 'phoenix', 'lucid']):
        return 'Text-to-Image'
    elif any(x in name_lower for x in ['whisper', 'nova-3', 'speech-recognition']):
        return 'Automatic Speech Recognition'
    elif any(x in name_lower for x in ['melotts', 'aura-', 'tts']):
        return 'Text-to-Speech'
    elif any(x in name_lower for x in ['bge-', 'embed', 'embedding']):
        return 'Text Embeddings'
    elif any(x in name_lower for x in ['llava', 'uform', 'image-to-text']):
        return 'Image-to-Text'
    elif any(x in name_lower for x in ['m2m100', 'indictrans', 'translation']):
        return 'Translation'
    elif any(x in name_lower for x in ['distilbert', 'sst-2', 'classification', 'reranker']):
        return 'Text Classification'
    elif any(x in name_lower for x in ['bart', 'summariz']):
        return 'Summarization'
    elif any(x in name_lower for x in ['detr', 'resnet', 'detection']):
        return 'Object Detection'
    elif any(x in name_lower for x in ['smart-turn', 'vad']):
        return 'Voice Activity Detection'
    else:
        return 'Text Generation'


def load_cached_models() -> List[Dict]:
    """Load models from cached models.json"""
    try:
        with open('models.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: models.json not found. Run with --fetch to get latest data.")
        sys.exit(1)


def save_models_cache(models: List[Dict]):
    """Save models to cache file"""
    with open('models.json', 'w') as f:
        json.dump(models, f, indent=2)
    print(f"✓ Saved {len(models)} models to models.json")


def get_modality(task_type: str, metadata: Dict) -> List[str]:
    """Convert Cloudflare task type to schema modalities"""
    task_to_modality = metadata.get('task_to_modality', {})
    modality = task_to_modality.get(task_type, 'text-to-text')
    return [modality]


def build_model_id(slug: str, author: Optional[str]) -> str:
    """Build the @cf/ prefixed model ID"""
    # The actual model ID format used by Cloudflare API
    # e.g., @cf/meta/llama-3-8b-instruct
    
    # Map known author names to their namespace
    author_namespaces = {
        'Meta': 'meta',
        'Google': 'google',
        'OpenAI': 'openai',
        'MistralAI': 'mistralai',
        'Qwen': 'qwen',
        'DeepSeek': 'deepseek-ai',
        'IBM': 'ibm-granite',
        'Microsoft': 'microsoft',
        'Deepgram': 'deepgram',
        'baai': 'baai',
        'Black Forest Labs': 'black-forest-labs',
        'Leonardo': 'leonardo',
        'Stability.ai': 'stabilityai',
    }
    
    if author and author in author_namespaces:
        namespace = author_namespaces[author]
        return f"@cf/{namespace}/{slug}"
    
    # Default: use slug as-is with common namespace inference
    if 'llama' in slug.lower() or 'llama-guard' in slug.lower():
        return f"@cf/meta/{slug}"
    elif 'gemma' in slug.lower():
        return f"@cf/google/{slug}"
    elif 'mistral' in slug.lower() or 'mixtral' in slug.lower():
        return f"@cf/mistralai/{slug}"
    elif 'qwen' in slug.lower() or 'qwq' in slug.lower():
        return f"@cf/qwen/{slug}"
    elif 'whisper' in slug.lower():
        return f"@cf/openai/{slug}"
    elif 'deepseek' in slug.lower():
        return f"@cf/deepseek-ai/{slug}"
    elif 'bge' in slug.lower():
        return f"@cf/baai/{slug}"
    elif 'flux' in slug.lower():
        return f"@cf/black-forest-labs/{slug}"
    elif 'granite' in slug.lower():
        return f"@cf/ibm-granite/{slug}"
    elif 'aura' in slug.lower() or 'nova-3' in slug.lower():
        return f"@cf/deepgram/{slug}"
    
    # Fallback: just use the slug
    return f"@cf/{slug}"


def generate_config(models: List[Dict], metadata: Dict) -> Dict:
    """Generate the config.yaml structure"""
    
    vision_models = set(metadata.get('vision_models', []))
    function_calling = set(metadata.get('function_calling_models', []))
    context_windows = metadata.get('context_windows', {})
    deprecated = set(metadata.get('deprecated_models', []))
    defaults = metadata.get('defaults', {})
    
    default_context = defaults.get('contextWindow', 8192)
    default_max_output = defaults.get('maxOutputTokens', 4096)
    
    config = {
        '$id': 'cloudflare',
        'name': 'Cloudflare Workers AI',
        'description': 'Cloudflare Workers AI - Run AI models at the edge with 10,000 free neurons/day',
        'url': 'https://ai.cloudflare.com',
        'docs': 'https://developers.cloudflare.com/workers-ai/',
        'auth': {
            'type': 'bearer',
            'keyLabel': 'Cloudflare API Token',
            'keyUrl': 'https://dash.cloudflare.com/profile/api-tokens',
        },
        'endpoint': {
            'baseUrl': 'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run',
            'protocol': 'custom',
            'notes': 'Replace {ACCOUNT_ID} with your Cloudflare account ID. Each model is called via POST to baseUrl/@cf/namespace/model-name'
        },
        'limits': {
            'neurons': {
                'perDay': 10000,
                'description': 'Free tier: 10,000 neurons per day (cost varies by model)'
            }
        },
        'models': []
    }
    
    processed_ids = set()
    
    for model in models:
        slug = model.get('slug', '')
        task_type = model.get('task_type', 'Text Generation')
        author = model.get('author')
        caps = model.get('capabilities', [])
        
        # Build the model ID
        model_id = build_model_id(slug, author)
        
        # Skip duplicates
        if model_id in processed_ids:
            continue
        processed_ids.add(model_id)
        
        # Skip deprecated models
        if model_id in deprecated or 'deprecated' in caps:
            continue
        
        # Get modalities
        modalities = get_modality(task_type, metadata)
        
        # Check if vision model (add image-to-text modality)
        is_vision = model_id in vision_models or 'vision' in slug.lower() or 'llava' in slug.lower()
        if is_vision and 'image-to-text' not in modalities:
            modalities.append('image-to-text')
        
        # Get context window
        context_window = context_windows.get(model_id, default_context)
        
        # Determine capabilities
        has_tools = model_id in function_calling or 'function_calling' in caps
        supports_streaming = task_type == 'Text Generation'  # Most text gen models support streaming
        
        model_entry = {
            'id': model_id,
            'upstream': model_id,
            'free': True,
            'modalities': modalities,
            'contextWindow': context_window,
            'maxOutputTokens': default_max_output,
            'capabilities': {
                'streaming': supports_streaming,
                'tools': has_tools,
                'vision': is_vision,
                'json': has_tools  # JSON mode typically available with tools
            }
        }
        
        # Add beta flag if applicable
        if 'beta' in caps:
            model_entry['beta'] = True
        
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
        f.write('# NOTE: Replace {ACCOUNT_ID} with your Cloudflare account ID\n')
        f.write('# Find it at: https://dash.cloudflare.com/ -> any zone -> Overview -> Account ID (right sidebar)\n')
        f.write('endpoint:\n')
        f.write(f'  baseUrl: "{config["endpoint"]["baseUrl"]}"\n')
        f.write(f'  protocol: "{config["endpoint"]["protocol"]}"\n')
        if 'notes' in config['endpoint']:
            f.write(f'  # {config["endpoint"]["notes"]}\n')
        f.write('\n')
        
        # Limits section
        f.write('# Cloudflare uses "neurons" as the billing unit\n')
        f.write('# Free tier: 10,000 neurons/day. Cost per request varies by model.\n')
        f.write('limits:\n')
        f.write('  neurons:\n')
        f.write(f'    perDay: {config["limits"]["neurons"]["perDay"]}\n')
        f.write(f'    description: "{config["limits"]["neurons"]["description"]}"\n\n')
        
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
            if model.get('beta'):
                f.write('    beta: true\n')
            f.write('\n')
        
        # Footer
        f.write('status: "active"\n')
        f.write('env: "CLOUDFLARE_API_TOKEN"\n')
        f.write('accountIdEnv: "CLOUDFLARE_ACCOUNT_ID"\n')
        f.write('tags:\n')
        f.write('  - free\n')
        f.write('  - edge\n')
        f.write('  - cloudflare\n')
    
    # Print summary
    print(f"✓ Generated {output_path} with {len(config['models'])} models")
    
    # Count by modality
    modality_counts = {}
    for model in config['models']:
        for mod in model['modalities']:
            modality_counts[mod] = modality_counts.get(mod, 0) + 1
    
    print("  Breakdown by modality:")
    for mod, count in sorted(modality_counts.items()):
        print(f"    - {mod}: {count}")
    
    vision_count = sum(1 for m in config['models'] if m['capabilities']['vision'])
    tools_count = sum(1 for m in config['models'] if m['capabilities']['tools'])
    print(f"  - Vision models: {vision_count}")
    print(f"  - Models with tools: {tools_count}")


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


def create_sample_models_json():
    """Create a sample models.json based on known Cloudflare models"""
    # This is a fallback when scraping doesn't work well
    # Based on the README.md pricing table and docs
    models = [
        # Text Generation - LLMs
        {"slug": "llama-3.2-1b-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.2-3b-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-8b-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-8b-instruct-fp8", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-8b-instruct-awq", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-8b-instruct-fast", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-70b-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.1-70b-instruct-fp8-fast", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3.2-11b-vision-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": ["lora"]},
        {"slug": "llama-3.3-70b-instruct-fp8-fast", "task_type": "Text Generation", "author": "Meta", "capabilities": ["batch", "function_calling"]},
        {"slug": "llama-4-scout-17b-16e-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": ["batch", "function_calling"]},
        {"slug": "llama-3-8b-instruct", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-3-8b-instruct-awq", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-2-7b-chat-fp16", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-2-7b-chat-int8", "task_type": "Text Generation", "author": "Meta", "capabilities": []},
        {"slug": "llama-guard-3-8b", "task_type": "Text Generation", "author": "Meta", "capabilities": ["lora"]},
        {"slug": "meta-llama-3-8b-instruct", "task_type": "Text Generation", "author": "meta-llama", "capabilities": []},
        
        # Google models
        {"slug": "gemma-3-12b-it", "task_type": "Text Generation", "author": "Google", "capabilities": ["lora"]},
        {"slug": "gemma-7b-it", "task_type": "Text Generation", "author": "Google", "capabilities": ["beta", "lora"]},
        {"slug": "gemma-7b-it-lora", "task_type": "Text Generation", "author": "Google", "capabilities": ["beta", "lora"]},
        {"slug": "gemma-2b-it-lora", "task_type": "Text Generation", "author": "Google", "capabilities": ["beta", "lora"]},
        {"slug": "embeddinggemma-300m", "task_type": "Text Embeddings", "author": "Google", "capabilities": []},
        
        # Mistral models
        {"slug": "mistral-7b-instruct-v0.1", "task_type": "Text Generation", "author": "MistralAI", "capabilities": ["lora"]},
        {"slug": "mistral-7b-instruct-v0.2", "task_type": "Text Generation", "author": "MistralAI", "capabilities": ["beta", "lora"]},
        {"slug": "mistral-7b-instruct-v0.2-lora", "task_type": "Text Generation", "author": "MistralAI", "capabilities": ["beta", "lora"]},
        {"slug": "mistral-small-3.1-24b-instruct", "task_type": "Text Generation", "author": "MistralAI", "capabilities": ["function_calling"]},
        
        # Qwen models
        {"slug": "qwq-32b", "task_type": "Text Generation", "author": "Qwen", "capabilities": ["lora"]},
        {"slug": "qwen2.5-coder-32b-instruct", "task_type": "Text Generation", "author": "Qwen", "capabilities": ["lora"]},
        {"slug": "qwen3-30b-a3b-fp8", "task_type": "Text Generation", "author": "Qwen", "capabilities": ["batch", "function_calling"]},
        {"slug": "qwen3-embedding-0.6b", "task_type": "Text Embeddings", "author": "Qwen", "capabilities": []},
        
        # OpenAI models
        {"slug": "gpt-oss-120b", "task_type": "Text Generation", "author": "OpenAI", "capabilities": []},
        {"slug": "gpt-oss-20b", "task_type": "Text Generation", "author": "OpenAI", "capabilities": []},
        {"slug": "whisper", "task_type": "Automatic Speech Recognition", "author": "OpenAI", "capabilities": []},
        {"slug": "whisper-large-v3-turbo", "task_type": "Automatic Speech Recognition", "author": "OpenAI", "capabilities": ["batch"]},
        {"slug": "whisper-tiny-en", "task_type": "Automatic Speech Recognition", "author": "OpenAI", "capabilities": ["beta"]},
        
        # DeepSeek models
        {"slug": "deepseek-r1-distill-qwen-32b", "task_type": "Text Generation", "author": "DeepSeek", "capabilities": []},
        
        # IBM models
        {"slug": "granite-4.0-h-micro", "task_type": "Text Generation", "author": "IBM", "capabilities": ["function_calling"]},
        
        # Other LLMs
        {"slug": "glm-4.7-flash", "task_type": "Text Generation", "author": "zai-org", "capabilities": ["function_calling"]},
        {"slug": "gemma-sea-lion-v4-27b-it", "task_type": "Text Generation", "author": "aisingapore", "capabilities": []},
        {"slug": "hermes-2-pro-mistral-7b", "task_type": "Text Generation", "author": "nousresearch", "capabilities": ["beta", "function_calling"]},
        {"slug": "phi-2", "task_type": "Text Generation", "author": "Microsoft", "capabilities": ["beta"]},
        {"slug": "sqlcoder-7b-2", "task_type": "Text Generation", "author": "defog", "capabilities": ["beta"]},
        
        # Text-to-Image models
        {"slug": "flux-1-schnell", "task_type": "Text-to-Image", "author": "Black Forest Labs", "capabilities": []},
        {"slug": "flux-2-dev", "task_type": "Text-to-Image", "author": "Black Forest Labs", "capabilities": ["partner"]},
        {"slug": "flux-2-klein-4b", "task_type": "Text-to-Image", "author": "Black Forest Labs", "capabilities": ["partner"]},
        {"slug": "flux-2-klein-9b", "task_type": "Text-to-Image", "author": "Black Forest Labs", "capabilities": ["partner"]},
        {"slug": "stable-diffusion-xl-base-1.0", "task_type": "Text-to-Image", "author": "Stability.ai", "capabilities": ["beta"]},
        {"slug": "stable-diffusion-xl-lightning", "task_type": "Text-to-Image", "author": "bytedance", "capabilities": ["beta"]},
        {"slug": "stable-diffusion-v1-5-img2img", "task_type": "Text-to-Image", "author": "runwayml", "capabilities": ["beta"]},
        {"slug": "stable-diffusion-v1-5-inpainting", "task_type": "Text-to-Image", "author": "runwayml", "capabilities": ["beta"]},
        {"slug": "dreamshaper-8-lcm", "task_type": "Text-to-Image", "author": "lykon", "capabilities": []},
        {"slug": "lucid-origin", "task_type": "Text-to-Image", "author": "Leonardo", "capabilities": ["partner"]},
        {"slug": "phoenix-1.0", "task_type": "Text-to-Image", "author": "Leonardo", "capabilities": ["partner"]},
        
        # Text-to-Speech models  
        {"slug": "melotts", "task_type": "Text-to-Speech", "author": "myshell-ai", "capabilities": []},
        {"slug": "aura-1", "task_type": "Text-to-Speech", "author": "Deepgram", "capabilities": ["batch", "partner", "realtime"]},
        {"slug": "aura-2-en", "task_type": "Text-to-Speech", "author": "Deepgram", "capabilities": ["batch", "partner", "realtime"]},
        {"slug": "aura-2-es", "task_type": "Text-to-Speech", "author": "Deepgram", "capabilities": ["batch", "partner", "realtime"]},
        
        # ASR models
        {"slug": "nova-3", "task_type": "Automatic Speech Recognition", "author": "Deepgram", "capabilities": ["batch", "partner", "realtime"]},
        {"slug": "flux", "task_type": "Automatic Speech Recognition", "author": "Deepgram", "capabilities": ["partner", "realtime"]},
        {"slug": "smart-turn-v2", "task_type": "Voice Activity Detection", "author": "pipecat-ai", "capabilities": ["batch", "realtime"]},
        
        # Embedding models
        {"slug": "bge-small-en-v1.5", "task_type": "Text Embeddings", "author": "baai", "capabilities": ["batch"]},
        {"slug": "bge-base-en-v1.5", "task_type": "Text Embeddings", "author": "baai", "capabilities": ["batch"]},
        {"slug": "bge-large-en-v1.5", "task_type": "Text Embeddings", "author": "baai", "capabilities": ["batch"]},
        {"slug": "bge-m3", "task_type": "Text Embeddings", "author": "baai", "capabilities": []},
        {"slug": "bge-reranker-base", "task_type": "Text Classification", "author": "baai", "capabilities": []},
        {"slug": "plamo-embedding-1b", "task_type": "Text Embeddings", "author": "pfnet", "capabilities": []},
        
        # Image-to-Text models
        {"slug": "llava-1.5-7b-hf", "task_type": "Image-to-Text", "author": "llava-hf", "capabilities": ["beta"]},
        {"slug": "uform-gen2-qwen-500m", "task_type": "Image-to-Text", "author": "unum", "capabilities": ["beta"]},
        
        # Translation models
        {"slug": "m2m100-1.2b", "task_type": "Translation", "author": "Meta", "capabilities": ["batch"]},
        {"slug": "indictrans2-en-indic-1B", "task_type": "Translation", "author": "ai4bharat", "capabilities": []},
        
        # Other models
        {"slug": "distilbert-sst-2-int8", "task_type": "Text Classification", "author": "HuggingFace", "capabilities": []},
        {"slug": "resnet-50", "task_type": "Image Classification", "author": "Microsoft", "capabilities": []},
        {"slug": "detr-resnet-50", "task_type": "Object Detection", "author": "facebook", "capabilities": ["beta"]},
        {"slug": "bart-large-cnn", "task_type": "Summarization", "author": "facebook", "capabilities": ["beta"]},
    ]
    
    return models


def main():
    args = sys.argv[1:]
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Load metadata
    metadata = load_metadata()
    
    # Fetch if requested
    if '--fetch' in args:
        if HAS_SCRAPING:
            models = fetch_models()
            if len(models) < 30:
                print("Warning: Scraping returned few models. Using curated fallback list.")
                models = create_sample_models_json()
        else:
            print("Using curated model list (scraping libraries not available)")
            models = create_sample_models_json()
        save_models_cache(models)
    else:
        # Try to load cached models
        try:
            models = load_cached_models()
        except SystemExit:
            print("Creating initial models.json from curated list...")
            models = create_sample_models_json()
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
