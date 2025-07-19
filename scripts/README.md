# VoiceApp Scripts Documentation 📜

This directory contains utility scripts for the VoiceApp backend API, focused on documentation generation and basic testing.

## 📁 **Available Scripts**

### **📚 Documentation Generation**

#### `generate_docs.py`
**Purpose:** Generate comprehensive API documentation from OpenAPI specification

**Usage:**
```bash
# Generate documentation for local server
python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./docs

# Generate for different environments
python3 scripts/generate_docs.py --base-url https://api.voiceapp.com --output-dir ./prod-docs
```

**Output:**
- `openapi.json` - OpenAPI 3.0 specification
- `VoiceApp_API.postman_collection.json` - Postman collection
- `VoiceApp_Environment.postman_environment.json` - Postman environment
- `api_docs.html` - Interactive Swagger UI documentation
- `README.md` - Documentation usage guide

#### `run_complete_test.sh`
**Purpose:** Run comprehensive testing and documentation generation pipeline

**Usage:**
```bash
# Full pipeline (testing + documentation)
./scripts/run_complete_test.sh

# Skip smoke tests, only generate docs
./scripts/run_complete_test.sh --skip-smoke

# Custom output directory
./scripts/run_complete_test.sh --output-dir ./custom-docs

# Verbose output
./scripts/run_complete_test.sh --verbose
```

**Options:**
- `--base-url URL` - API base URL (default: http://localhost:8000)
- `--output-dir DIR` - Documentation output directory (default: ./docs)
- `--skip-smoke` - Skip smoke tests
- `--verbose` - Enable verbose output
- `--help` - Show help message

#### `run_smoke_tests.sh`
**Purpose:** Quick smoke tests to verify API functionality

**Usage:**
```bash
# Test local server
./scripts/run_smoke_tests.sh

# Test different environment
./scripts/run_smoke_tests.sh --base-url https://staging-api.voiceapp.com

# Verbose output
./scripts/run_smoke_tests.sh --verbose
```

#### `smoke_test.py`
**Purpose:** Comprehensive API testing suite

**Usage:**
```bash
# Run all tests
python3 scripts/smoke_test.py --base-url http://localhost:8000

# Verbose output
python3 scripts/smoke_test.py --base-url http://localhost:8000 --verbose
```

**Test Coverage:**
- Health checks
- Authentication endpoints
- AI services (topic extraction, TTS)
- Room management
- Matching system
- WebSocket connections

## 🚀 **Quick Start**

### **1. Generate Documentation**
```bash
# Start your VoiceApp server
python3 main.py

# Generate fresh documentation
python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./api-docs

# View documentation
open ./api-docs/api_docs.html
```

### **2. Test API Functionality**
```bash
# Quick smoke test
./scripts/run_smoke_tests.sh

# Complete test and docs
./scripts/run_complete_test.sh
```

### **3. Import to Postman**
1. Open Postman
2. Click "Import"
3. Select `./api-docs/VoiceApp_API.postman_collection.json`
4. Import environment: `./api-docs/VoiceApp_Environment.postman_environment.json`

## 📋 **Prerequisites**

### **Required Dependencies**
```bash
pip install aiohttp websockets requests firebase-admin
```

### **Environment Setup**
Make sure your VoiceApp server is running before using these scripts:
```bash
python3 main.py
```

## 🎯 **Common Use Cases**

### **Frontend Developer Workflow**
```bash
# 1. Generate latest API docs
./scripts/run_complete_test.sh --skip-smoke --output-dir ./frontend-docs

# 2. Import Postman collection
# Use: ./frontend-docs/VoiceApp_API.postman_collection.json

# 3. Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i ./frontend-docs/openapi.json \
  -g typescript-axios \
  -o ./src/api
```

### **API Documentation Updates**
```bash
# After API changes, regenerate docs
python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./docs

# Verify with smoke tests
./scripts/run_smoke_tests.sh --verbose
```

### **Integration Testing**
```bash
# Test against staging environment
./scripts/run_smoke_tests.sh --base-url https://staging-api.voiceapp.com

# Generate staging docs
python3 scripts/generate_docs.py --base-url https://staging-api.voiceapp.com --output-dir ./staging-docs
```

## 🔧 **Script Configuration**

### **Environment Variables**
```bash
# Optional: Override default settings
export API_BASE_URL=http://localhost:8000
export DOCS_OUTPUT_DIR=./docs
export VERBOSE_OUTPUT=true
```

### **Customization**
Each script accepts command-line arguments to override defaults:
- `--base-url` - API server URL
- `--output-dir` - Documentation output directory
- `--verbose` - Enable detailed logging
- `--help` - Show usage information

## 📊 **Output Structure**

After running documentation generation:
```
./docs/
├── api_docs.html                           # Interactive documentation
├── openapi.json                           # OpenAPI specification
├── VoiceApp_API.postman_collection.json   # Postman collection
├── VoiceApp_Environment.postman_environment.json  # Postman environment
└── README.md                              # Usage instructions
```

## 🎉 **Happy Documenting!**

These scripts ensure your API documentation is always up-to-date and your integration tests are comprehensive. Perfect for maintaining high-quality frontend-backend integration! 🚀 