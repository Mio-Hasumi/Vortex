#!/usr/bin/env python3
"""
VoiceApp API Documentation Generator
===================================

Generates API documentation and exports:
- OpenAPI/Swagger JSON
- Postman Collection (with WebSocket support)
- Interactive HTML docs
- WebSocket testing examples

Usage:
    python scripts/generate_docs.py
    python scripts/generate_docs.py --base-url https://your-api.com
    python scripts/generate_docs.py --output-dir ./docs
"""

import json
import os
import sys
import argparse
import requests
from datetime import datetime
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIDocumentationGenerator:
    """Generate comprehensive API documentation"""
    
    def __init__(self, base_url: str = "http://localhost:8000", output_dir: str = "./docs"):
        self.base_url = base_url.rstrip('/')
        self.ws_base_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.output_dir = output_dir
        self.openapi_spec = None
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def fetch_openapi_spec(self):
        """Fetch OpenAPI specification from the server"""
        try:
            logger.info(f"🔍 Fetching OpenAPI spec from {self.base_url}/openapi.json")
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            response.raise_for_status()
            
            self.openapi_spec = response.json()
            
            # Add WebSocket endpoints manually since OpenAPI 3.0 doesn't support them natively
            self.add_websocket_endpoints()
            
            logger.info("✅ OpenAPI specification fetched successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch OpenAPI spec: {e}")
            logger.info("💡 Make sure the server is running and accessible")
            return False
    
    def add_websocket_endpoints(self):
        """Add WebSocket endpoints to OpenAPI spec"""
        if not self.openapi_spec:
            return
        
        websocket_paths = {
            "/api/ai-host/voice-chat": {
                "websocket": {
                    "summary": "Real-time voice chat with GPT-4o Realtime Preview",
                    "description": "WebSocket endpoint for real-time voice communication with AI host using GPT-4o Realtime Preview",
                    "tags": ["AI Host"],
                    "parameters": [
                        {
                            "name": "Authorization",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Firebase ID token"
                        }
                    ],
                    "requestBody": {
                        "description": "Voice data and control messages",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["voice_data", "control"],
                                            "description": "Message type"
                                        },
                                        "data": {
                                            "type": "string",
                                            "description": "Base64 encoded audio data"
                                        },
                                        "format": {
                                            "type": "string",
                                            "enum": ["wav", "mp3"],
                                            "description": "Audio format"
                                        },
                                        "sample_rate": {
                                            "type": "integer",
                                            "default": 16000,
                                            "description": "Audio sample rate"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "101": {
                            "description": "WebSocket connection established"
                        }
                    }
                }
            }
        }
        
        # Add WebSocket paths to OpenAPI spec
        self.openapi_spec["paths"].update(websocket_paths)

    def save_openapi_json(self):
        """Save OpenAPI specification as JSON"""
        if not self.openapi_spec:
            return False
        
        try:
            output_path = os.path.join(self.output_dir, "openapi.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.openapi_spec, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ OpenAPI JSON saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save OpenAPI JSON: {e}")
            return False
    
    def generate_postman_collection(self):
        """Generate Postman collection from OpenAPI spec"""
        if not self.openapi_spec:
            return False
        
        try:
            logger.info("🔧 Generating Postman collection...")
            
            collection = {
                "info": {
                    "name": self.openapi_spec.get("info", {}).get("title", "VoiceApp API"),
                    "description": self.openapi_spec.get("info", {}).get("description", "AI-powered voice social platform API"),
                    "version": self.openapi_spec.get("info", {}).get("version", "1.0.0"),
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
                },
                "variable": [
                    {
                        "key": "base_url",
                        "value": self.base_url,
                        "type": "string"
                    },
                    {
                        "key": "ws_base_url",
                        "value": self.ws_base_url,
                        "type": "string"
                    },
                    {
                        "key": "firebase_token",
                        "value": "your_firebase_id_token_here",
                        "type": "string"
                    }
                ],
                "auth": {
                    "type": "bearer",
                    "bearer": [
                        {
                            "key": "token",
                            "value": "{{firebase_token}}",
                            "type": "string"
                        }
                    ]
                },
                "item": []
            }
            
            # Group endpoints by tags
            folders = {}
            
            for path, methods in self.openapi_spec.get("paths", {}).items():
                for method, endpoint_spec in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'WEBSOCKET']:
                        tags = endpoint_spec.get("tags", ["Other"])
                        tag = tags[0] if tags else "Other"
                        
                        if tag not in folders:
                            folders[tag] = {
                                "name": tag.title(),
                                "item": []
                            }
                        
                        # Create Postman request
                        request_item = self.create_postman_request(path, method.upper(), endpoint_spec)
                        folders[tag]["item"].append(request_item)
            
            # Add WebSocket example folder
            folders["WebSocket Examples"] = self.create_websocket_examples()
            
            # Add folders to collection
            collection["item"] = list(folders.values())
            
            # Save Postman collection
            output_path = os.path.join(self.output_dir, "VoiceApp_API.postman_collection.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(collection, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Postman collection saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate Postman collection: {e}")
            return False

    def create_websocket_examples(self) -> Dict[str, Any]:
        """Create WebSocket example requests for Postman"""
        return {
            "name": "WebSocket Examples",
            "item": [
                {
                    "name": "Voice Chat with GPT-4o",
                    "request": {
                        "method": "WEBSOCKET",
                        "header": [
                            {
                                "key": "Authorization",
                                "value": "{{firebase_token}}"
                            }
                        ],
                        "url": {
                            "raw": "{{ws_base_url}}/api/ai-host/voice-chat",
                            "host": ["{{ws_base_url}}"],
                            "path": ["api", "ai-host", "voice-chat"]
                        },
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "type": "voice_data",
                                "data": "<base64_audio_data>",
                                "format": "wav",
                                "sample_rate": 16000
                            }, indent=2)
                        }
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "type": "text/javascript",
                                "exec": [
                                    "// Example WebSocket test script",
                                    "console.log('Connected to voice chat WebSocket');",
                                    "",
                                    "// Handle incoming messages",
                                    "pm.ws.onMessage((message) => {",
                                    "    const response = JSON.parse(message);",
                                    "    console.log('Received:', response);",
                                    "    ",
                                    "    if (response.type === 'transcription') {",
                                    "        console.log('User said:', response.text);",
                                    "    } else if (response.type === 'ai_response') {",
                                    "        console.log('AI response:', response.text);",
                                    "        // Audio response available at response.audio_url",
                                    "    }",
                                    "});"
                                ]
                            }
                        }
                    ]
                }
            ]
        }

    def create_postman_request(self, path: str, method: str, endpoint_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Postman request item from OpenAPI endpoint spec"""
        
        # Replace path parameters with Postman variables
        postman_path = path
        parameters = endpoint_spec.get("parameters", [])
        path_params = [p for p in parameters if p.get("in") == "path"]
        
        for param in path_params:
            param_name = param.get("name")
            postman_path = postman_path.replace(f"{{{param_name}}}", f"{{{{{param_name}}}}}")
        
        # Build URL
        url_parts = {
            "raw": f"{{{{base_url}}}}{postman_path}",
            "host": ["{{base_url}}"],
            "path": [part for part in postman_path.strip("/").split("/") if part]
        }
        
        # Add query parameters
        query_params = [p for p in parameters if p.get("in") == "query"]
        if query_params:
            url_parts["query"] = []
            for param in query_params:
                url_parts["query"].append({
                    "key": param.get("name"),
                    "value": param.get("example", f"<{param.get('name')}>"),
                    "disabled": not param.get("required", False)
                })
        
        # Build headers
        headers = []
        if method in ['POST', 'PUT', 'PATCH']:
            headers.append({
                "key": "Content-Type",
                "value": "application/json"
            })
        
        # Add custom headers from parameters
        header_params = [p for p in parameters if p.get("in") == "header"]
        for param in header_params:
            if param.get("name").lower() != "authorization":  # Skip auth header (handled by collection auth)
                headers.append({
                    "key": param.get("name"),
                    "value": param.get("example", f"<{param.get('name')}>")
                })
        
        # Build request body
        body = None
        request_body = endpoint_spec.get("requestBody")
        if request_body and method in ['POST', 'PUT', 'PATCH']:
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                body = {
                    "mode": "raw",
                    "raw": json.dumps(self.generate_example_from_schema(schema), indent=2),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
            elif "multipart/form-data" in content:
                body = {
                    "mode": "formdata",
                    "formdata": [
                        {
                            "key": "file",
                            "type": "file",
                            "src": []
                        }
                    ]
                }
        
        # Build the request
        request_item = {
            "name": endpoint_spec.get("summary", f"{method} {path}"),
            "request": {
                "method": method,
                "header": headers,
                "url": url_parts
            },
            "response": []
        }
        
        if body:
            request_item["request"]["body"] = body
        
        # Add description
        description = endpoint_spec.get("description", "")
        if description:
            request_item["request"]["description"] = description
        
        return request_item
    
    def generate_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Generate example data from JSON schema"""
        if not schema:
            return {}
        
        schema_type = schema.get("type")
        
        if schema_type == "object":
            example = {}
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for prop_name, prop_schema in properties.items():
                if prop_name in required or prop_schema.get("example") is not None:
                    example[prop_name] = self.generate_example_from_schema(prop_schema)
            
            return example
        
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            return [self.generate_example_from_schema(items_schema)]
        
        elif schema_type == "string":
            if schema.get("format") == "email":
                return "user@example.com"
            elif schema.get("format") == "uuid":
                return "12345678-1234-5678-9012-123456789012"
            elif schema.get("format") == "date-time":
                return "2023-12-01T10:00:00Z"
            else:
                return schema.get("example", "string")
        
        elif schema_type == "integer":
            return schema.get("example", 1)
        
        elif schema_type == "number":
            return schema.get("example", 1.0)
        
        elif schema_type == "boolean":
            return schema.get("example", True)
        
        else:
            return schema.get("example", "value")
    
    def generate_html_docs(self):
        """Generate interactive HTML documentation"""
        if not self.openapi_spec:
            return False
        
        try:
            logger.info("📝 Generating HTML documentation...")
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.openapi_spec.get('info', {}).get('title', 'API Documentation')}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {json.dumps(self.openapi_spec)},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>"""
            
            output_path = os.path.join(self.output_dir, "api_docs.html")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ HTML documentation saved to: {output_path}")
            logger.info(f"🌐 Open in browser: file://{os.path.abspath(output_path)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate HTML docs: {e}")
            return False
    
    def generate_postman_environment(self):
        """Generate Postman environment file"""
        try:
            environment = {
                "id": "voiceapp-environment",
                "name": "VoiceApp Environment",
                "values": [
                    {
                        "key": "base_url",
                        "value": self.base_url,
                        "enabled": True,
                        "type": "default"
                    },
                    {
                        "key": "firebase_token",
                        "value": "",
                        "enabled": True,
                        "type": "secret"
                    },
                    {
                        "key": "user_id",
                        "value": "",
                        "enabled": True,
                        "type": "default"
                    },
                    {
                        "key": "room_id",
                        "value": "",
                        "enabled": True,
                        "type": "default"
                    }
                ],
                "_postman_variable_scope": "environment"
            }
            
            output_path = os.path.join(self.output_dir, "VoiceApp_Environment.postman_environment.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(environment, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Postman environment saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate Postman environment: {e}")
            return False
    
    def generate_readme(self):
        """Generate README for the documentation"""
        try:
            readme_content = f"""# VoiceApp API Documentation

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
API Base URL: {self.base_url}

## 📁 Files

- **`openapi.json`** - OpenAPI 3.0 specification
- **`VoiceApp_API.postman_collection.json`** - Postman collection
- **`VoiceApp_Environment.postman_environment.json`** - Postman environment
- **`api_docs.html`** - Interactive HTML documentation

## 🚀 Quick Start

### Option 1: Postman
1. Import `VoiceApp_API.postman_collection.json` into Postman
2. Import `VoiceApp_Environment.postman_environment.json` as environment
3. Set your Firebase ID token in the environment variables
4. Start testing the API!

### Option 2: Swagger UI
1. Open `api_docs.html` in your browser
2. Use the "Try it out" feature to test endpoints
3. Set your Firebase bearer token for protected endpoints

### Option 3: Direct Integration
1. Use `openapi.json` with any OpenAPI-compatible tool
2. Import into your favorite API client
3. Generate client SDKs using OpenAPI generators

## 🔑 Authentication

Most endpoints require Firebase authentication:

1. **Get Firebase ID Token**:
   ```bash
   # Use the test token generator
   python generate_test_token.py
   ```

2. **Set in Postman**:
   - Go to Environment variables
   - Set `firebase_token` to your ID token

3. **Use in requests**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \\
        {self.base_url}/api/auth/profile
   ```

## 📡 WebSocket Endpoints

The API includes several WebSocket endpoints:

- **AI Live Subtitle**: `ws://localhost:8000/api/ai-host/live-subtitle`
- **AI Voice Chat**: `ws://localhost:8000/api/ai-host/voice-chat`
- **Room Communication**: `ws://localhost:8000/api/rooms/ws/{{room_id}}`
- **Matching Queue**: `ws://localhost:8000/api/matching/ws?user_id={{user_id}}`
- **General Notifications**: `ws://localhost:8000/api/matching/ws/general?user_id={{user_id}}`

## 🧪 Testing

Run comprehensive smoke tests:
```bash
# Local testing
./scripts/run_smoke_tests.sh

# Remote testing
./scripts/run_smoke_tests.sh --base-url https://your-api.com
```

## 📚 Additional Resources

- [Complete Frontend API Guide](../FRONTEND_API_GUIDE.md)
- [Testing Documentation](../TESTING.md)
- [Project README](../README.md)

---

*Documentation automatically generated from OpenAPI specification*
"""
            
            output_path = os.path.join(self.output_dir, "README.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            logger.info(f"✅ Documentation README saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate README: {e}")
            return False
    
    def generate_all(self):
        """Generate all documentation formats"""
        logger.info("📚 Generating API documentation...")
        logger.info(f"🎯 Target: {self.base_url}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 50)
        
        success_count = 0
        total_count = 6
        
        # Fetch OpenAPI spec first
        if self.fetch_openapi_spec():
            success_count += 1
        else:
            logger.error("💥 Cannot proceed without OpenAPI specification")
            return False
        
        # Generate all formats
        generators = [
            ("OpenAPI JSON", self.save_openapi_json),
            ("Postman Collection", self.generate_postman_collection),
            ("Postman Environment", self.generate_postman_environment),
            ("HTML Documentation", self.generate_html_docs),
            ("Documentation README", self.generate_readme)
        ]
        
        for name, generator in generators:
            logger.info(f"🔧 Generating {name}...")
            if generator():
                success_count += 1
            else:
                logger.error(f"❌ Failed to generate {name}")
        
        # Summary
        logger.info("=" * 50)
        logger.info(f"📊 Documentation Generation Results:")
        logger.info(f"   ✅ Success: {success_count}/{total_count}")
        logger.info(f"   📁 Output Directory: {os.path.abspath(self.output_dir)}")
        
        if success_count == total_count:
            logger.info("🎉 All documentation generated successfully!")
            logger.info(f"🌐 View docs: file://{os.path.abspath(os.path.join(self.output_dir, 'api_docs.html'))}")
            return True
        else:
            logger.info(f"⚠️ Some documentation generation failed ({success_count}/{total_count} succeeded)")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate VoiceApp API Documentation')
    parser.add_argument('--base-url', 
                       default='http://localhost:8000',
                       help='Base URL for the API (default: http://localhost:8000)')
    parser.add_argument('--output-dir', 
                       default='./docs',
                       help='Output directory for documentation (default: ./docs)')
    
    args = parser.parse_args()
    
    generator = APIDocumentationGenerator(
        base_url=args.base_url,
        output_dir=args.output_dir
    )
    
    success = generator.generate_all()
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Documentation generation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Documentation generation crashed: {e}")
        sys.exit(1) 