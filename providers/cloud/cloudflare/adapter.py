#!/usr/bin/env python3
"""
Cloudflare Workers AI OpenAI-Compatible Adapter

This adapter reads the protocol.yaml spec and provides an OpenAI-compatible
interface to Cloudflare's Workers AI API.

Usage:
    # As a module
    from adapter import CloudflareAdapter
    
    client = CloudflareAdapter()
    response = client.chat.completions.create(
        model="@cf/meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    
    # As a proxy server (optional)
    python adapter.py --serve --port 8080
    # Then use: OPENAI_BASE_URL=http://localhost:8080/v1

Requirements:
    pip install requests pyyaml
"""
import os
import json
import time
import uuid
import yaml
import requests
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass
from pathlib import Path


def load_dotenv():
    """Load environment variables from .env file in project root"""
    # Look for .env in parent directories
    current = Path(__file__).parent
    for _ in range(5):  # Search up to 5 levels
        env_file = current / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:  # Don't override existing
                            os.environ[key] = value
            return
        current = current.parent

# Load .env on module import
load_dotenv()

def load_protocol_spec() -> Dict:
    """Load the protocol specification"""
    spec_path = Path(__file__).parent / "protocol.yaml"
    with open(spec_path) as f:
        return yaml.safe_load(f)


@dataclass
class Message:
    role: str
    content: str


@dataclass  
class Choice:
    index: int
    message: Message
    finish_reason: str


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletion:
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": c.index,
                    "message": {"role": c.message.role, "content": c.message.content},
                    "finish_reason": c.finish_reason
                }
                for c in self.choices
            ],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens
            }
        }


class ChatCompletions:
    """OpenAI-compatible chat.completions interface"""
    
    def __init__(self, adapter: "CloudflareAdapter"):
        self.adapter = adapter
        self.spec = adapter.spec
    
    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs  # Ignore unsupported params
    ) -> ChatCompletion | Generator:
        """Create a chat completion"""
        
        # Build URL from spec
        url_template = self.spec["url"]["template"]
        url = url_template.format(
            account_id=self.adapter.account_id,
            model=model
        )
        
        # Build request body (only passthrough fields)
        body = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        
        # Build headers
        headers = {
            "Authorization": f"Bearer {self.adapter.api_key}",
            "Content-Type": "application/json"
        }
        
        if stream:
            return self._stream_response(url, headers, body, model)
        else:
            return self._sync_response(url, headers, body, model)
    
    def _sync_response(self, url: str, headers: Dict, body: Dict, model: str) -> ChatCompletion:
        """Handle non-streaming response"""
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        
        # Transform Cloudflare response to OpenAI format
        if not data.get("success", False):
            errors = data.get("errors", [])
            error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
            raise Exception(f"Cloudflare API error: {error_msg}")
        
        result = data.get("result", {})
        content = result.get("response", "")
        
        # Get usage if available
        usage_data = result.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )
        
        return ChatCompletion(
            id=f"chatcmpl-cf-{uuid.uuid4().hex[:8]}",
            object="chat.completion",
            created=int(time.time()),
            model=model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=content),
                    finish_reason="stop"
                )
            ],
            usage=usage
        )
    
    def _stream_response(self, url: str, headers: Dict, body: Dict, model: str) -> Generator:
        """Handle streaming response"""
        response = requests.post(url, headers=headers, json=body, stream=True)
        response.raise_for_status()
        
        request_id = f"chatcmpl-cf-{uuid.uuid4().hex[:8]}"
        created = int(time.time())
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    # Send final chunk with finish_reason
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    break
                
                try:
                    data = json.loads(data_str)
                    content = data.get("response", "")
                    
                    yield {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None
                        }]
                    }
                except json.JSONDecodeError:
                    continue


class Embeddings:
    """OpenAI-compatible embeddings interface"""
    
    def __init__(self, adapter: "CloudflareAdapter"):
        self.adapter = adapter
    
    def create(
        self,
        model: str,
        input: str | List[str],
        **kwargs
    ) -> Dict:
        """Create embeddings"""
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.adapter.account_id}/ai/run/{model}"
        
        # Cloudflare uses "text" instead of "input"
        if isinstance(input, str):
            body = {"text": input}
        else:
            body = {"text": input}
        
        headers = {
            "Authorization": f"Bearer {self.adapter.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success", False):
            raise Exception(f"Cloudflare API error: {data.get('errors', [])}")
        
        result = data.get("result", {})
        embeddings_data = result.get("data", [[]])
        
        # Transform to OpenAI format
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": emb,
                    "index": i
                }
                for i, emb in enumerate(embeddings_data)
            ],
            "model": model,
            "usage": {
                "prompt_tokens": 0,
                "total_tokens": 0
            }
        }


class Chat:
    """OpenAI-compatible chat interface"""
    
    def __init__(self, adapter: "CloudflareAdapter"):
        self.completions = ChatCompletions(adapter)


class CloudflareAdapter:
    """
    OpenAI-compatible adapter for Cloudflare Workers AI
    
    Usage:
        client = CloudflareAdapter()
        response = client.chat.completions.create(
            model="@cf/meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response.choices[0].message.content)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get("CLOUDFLARE_AI_API_KEY")
        self.account_id = account_id or os.environ.get("CLOUDFLARE_AI_ACCOUNT_ID")
        
        if not self.api_key:
            raise ValueError("CLOUDFLARE_AI_API_KEY not set")
        if not self.account_id:
            raise ValueError("CLOUDFLARE_AI_ACCOUNT_ID not set")
        
        self.spec = load_protocol_spec()
        self.chat = Chat(self)
        self.embeddings = Embeddings(self)
    
    def list_models(self) -> List[Dict]:
        """List available models (from config.yaml)"""
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        return {
            "object": "list",
            "data": [
                {
                    "id": m["id"],
                    "object": "model",
                    "created": 0,
                    "owned_by": "cloudflare"
                }
                for m in config.get("models", [])
            ]
        }


# Simple HTTP server for proxy mode
def serve_proxy(port: int = 8080):
    """Run as an OpenAI-compatible proxy server"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    adapter = CloudflareAdapter()
    
    class ProxyHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            
            if self.path == "/v1/chat/completions":
                try:
                    stream = body.get("stream", False)
                    result = adapter.chat.completions.create(**body)
                    
                    if stream:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        
                        for chunk in result:
                            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                        self.wfile.write(b"data: [DONE]\n\n")
                    else:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(result.to_dict()).encode())
                        
                except Exception as e:
                    self.send_error(500, str(e))
            
            elif self.path == "/v1/embeddings":
                try:
                    result = adapter.embeddings.create(**body)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                except Exception as e:
                    self.send_error(500, str(e))
            else:
                self.send_error(404, "Not found")
        
        def do_GET(self):
            if self.path == "/v1/models":
                result = adapter.list_models()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_error(404, "Not found")
    
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"Starting OpenAI-compatible proxy on http://localhost:{port}")
    print(f"Use: OPENAI_BASE_URL=http://localhost:{port}/v1")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    
    if "--serve" in sys.argv:
        port = 8080
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        serve_proxy(port)
    else:
        # Quick test
        client = CloudflareAdapter()
        print("Testing Cloudflare adapter...")
        
        response = client.chat.completions.create(
            model="@cf/meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "Say 'Hello from Cloudflare!' in exactly 5 words."}],
            max_tokens=50
        )
        
        print(f"Response: {response.choices[0].message.content}")
