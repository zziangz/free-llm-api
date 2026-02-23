#!/usr/bin/env python3
"""
GitHub Models Registry Updater

Fetches model list from GitHub Marketplace pages.

Usage:
    python update.py                # Scrape marketplace
    python update.py --test MODEL   # Test a specific model
"""
import json
import re
import subprocess
import sys
import os
from pathlib import Path


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


def fetch_marketplace_models(max_pages: int = 10) -> list:
    """Fetch model paths from GitHub Marketplace pages."""
    models = set()
    
    for page in range(1, max_pages + 1):
        try:
            result = subprocess.run(
                ["curl", "-s", f"https://github.com/marketplace?page={page}&type=models"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Extract model paths from marketplace links
            pattern = r'href="/marketplace/models/([^/"]+/[^/"]+)"'
            matches = re.findall(pattern, result.stdout)
            
            prev_count = len(models)
            for match in matches:
                models.add(match)
            
            # Check if page had new models
            if len(models) == prev_count:
                break
                
        except Exception as e:
            print(f"Warning: Failed to fetch page {page}: {e}")
            break
    
    return sorted(models)


def parse_model_info(model_path: str) -> dict | None:
    """Parse model path into structured info."""
    parts = model_path.split("/")
    if len(parts) != 2:
        return None
        
    publisher = parts[0]
    model_name = parts[1]
    
    # Skip embedding models
    if "embed" in model_name.lower():
        return None
    
    # Normalize publisher name
    pub_normalized = publisher.replace("azure-", "").replace("azureml-", "")
    
    # Determine modalities based on model name
    modalities = ["text-to-text"]
    vision_keywords = ["vision", "multimodal", "4o", "4.1", "gpt-5"]
    if any(kw.lower() in model_name.lower() for kw in vision_keywords):
        modalities.append("image-to-text")
    
    return {
        "id": model_name,
        "publisher": pub_normalized,
        "modalities": modalities,
        "free": True
    }


def test_model(model_id: str):
    """Test a specific model with the API."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GITHUB_PERSONAL_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN not set")
        return
    
    print(f"Testing model: {model_id}")
    cmd = [
        'curl', '-s', '-X', 'POST',
        'https://models.github.ai/inference/chat/completions',
        '-H', 'Content-Type: application/json',
        '-H', f'Authorization: Bearer {token}',
        '-d', json.dumps({
            "messages": [{"role": "user", "content": "Say hi"}],
            "model": model_id,
            "max_tokens": 10
        })
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout[:500])


def main():
    script_dir = Path(__file__).parent
    output_file = script_dir / "models.json"
    
    # Check for test flag
    if len(sys.argv) > 2 and sys.argv[1] == '--test':
        test_model(sys.argv[2])
        return
    
    print("Fetching models from GitHub Marketplace...")
    model_paths = fetch_marketplace_models()
    print(f"Found {len(model_paths)} model paths")
    
    models = []
    for path in model_paths:
        info = parse_model_info(path)
        if info:
            models.append(info)
    
    # Sort by publisher, then by model name
    models.sort(key=lambda x: (x["publisher"], x["id"]))
    
    # Remove duplicates (same model ID)
    seen = set()
    unique_models = []
    for model in models:
        if model["id"] not in seen:
            seen.add(model["id"])
            unique_models.append(model)
    
    print(f"Writing {len(unique_models)} unique models to {output_file}")
    
    with open(output_file, "w") as f:
        json.dump(unique_models, f, indent=2)
    
    # Group by publisher for summary
    publishers = {}
    for model in unique_models:
        pub = model["publisher"]
        publishers[pub] = publishers.get(pub, 0) + 1
    
    print("\nModels by publisher:")
    for pub, count in sorted(publishers.items()):
        print(f"  {pub}: {count}")
    
    # Vision models count
    vision_count = len([m for m in unique_models if "image-to-text" in m["modalities"]])
    print(f"\nTotal: {len(unique_models)} models ({vision_count} with vision)")


if __name__ == "__main__":
    main()
