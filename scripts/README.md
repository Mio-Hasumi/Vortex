# VoiceApp Scripts

This directory contains automated scripts for testing, documentation generation, and quality assurance of the VoiceApp backend API.

## 🚀 Quick Start

### One-Command Full Pipeline
```bash
# Run everything: smoke tests + documentation generation
./scripts/run_complete_test.sh

# Test production API
./scripts/run_complete_test.sh --base-url https://your-api.com

# Verbose output with custom docs directory
./scripts/run_complete_test.sh --verbose --output-dir ./api-docs
```

### Individual Scripts
```bash
# Smoke tests only
./scripts/run_smoke_tests.sh

# Documentation generation only
python scripts/generate_docs.py

# Advanced smoke testing
python scripts/smoke_test.py --verbose --base-url https://api.example.com
```

## 📁 Scripts Overview

### 🔥 `run_complete_test.sh` - Complete Pipeline
**The main script that runs everything in sequence**

```bash
./scripts/run_complete_test.sh [OPTIONS]

Options:
  --base-url URL       API base URL (default: http://localhost:8000)
  --verbose, -v        Enable verbose output
  --skip-docs          Skip documentation generation
  --skip-smoke         Skip smoke tests
  --output-dir DIR     Documentation output directory (default: ./docs)
  --help, -h           Show help message
```

**What it does:**
1. ✅ Checks prerequisites (Python, dependencies, virtual env)
2. 🔍 Verifies server health
3. 🔥 Runs comprehensive smoke tests
4. 📚 Generates complete API documentation
5. 📊 Provides detailed summary and next steps

**Examples:**
```bash
# Full pipeline on local server
./scripts/run_complete_test.sh

# Test production with verbose output
./scripts/run_complete_test.sh --base-url https://api.voiceapp.com --verbose

# Only smoke tests (skip docs)
./scripts/run_complete_test.sh --skip-docs

# Only documentation (skip tests)
./scripts/run_complete_test.sh --skip-smoke
```

### 🧪 `smoke_test.py` - Comprehensive API Testing
**Advanced smoke tests covering all major API functionality**

```bash
python scripts/smoke_test.py [OPTIONS]

Options:
  --base-url URL       API base URL (default: http://localhost:8000)
  --verbose, -v        Enable verbose logging
  --help, -h           Show help message
```

**Test Coverage:**
- ✅ Health checks (root + AI host endpoints)
- 🔐 Authentication (Firebase user creation, register, login, profile)
- 🤖 AI Services (topic extraction, TTS, simple test endpoint)
- 🏠 Room Management (create, join, details, list, WebSocket)
- 🎯 Matching System (traditional, AI-driven, status, timeout stats)
- 🏷️ Topics & Social (topics list, popular topics, friends list)

**What it tests:**
1. **Authentication Flow**: Creates Firebase user → Registers → Logs in → Gets profile
2. **AI Capabilities**: Extracts topics from text → Generates TTS audio → Tests endpoints
3. **Room Features**: Creates room → Gets details → Lists rooms → Tests WebSocket connection
4. **Matching Logic**: Requests match → Checks status → Tests AI matching → Verifies timeout handling
5. **Social Features**: Lists topics → Gets popular topics → Checks friends functionality

**Exit Codes:**
- `0`: All tests passed
- `1`: Tests passed with warnings
- `2`: Tests failed

### 🛠️ `run_smoke_tests.sh` - Simple Smoke Test Runner
**Simplified wrapper for smoke tests with dependency checking**

```bash
./scripts/run_smoke_tests.sh [OPTIONS]

Options:
  --base-url URL       API base URL (default: http://localhost:8000)
  --verbose, -v        Enable verbose output
  --help, -h           Show help message
```

**Features:**
- 📦 Automatic dependency installation
- 🔍 Server health check
- 🎨 Colored output
- ⚡ Quick execution

### 📚 `generate_docs.py` - API Documentation Generator
**Comprehensive documentation generator supporting multiple formats**

```bash
python scripts/generate_docs.py [OPTIONS]

Options:
  --base-url URL       API base URL (default: http://localhost:8000)
  --output-dir DIR     Output directory (default: ./docs)
  --help, -h           Show help message
```

**Generated Documentation:**
1. **`openapi.json`** - OpenAPI 3.0 specification
2. **`VoiceApp_API.postman_collection.json`** - Complete Postman collection
3. **`VoiceApp_Environment.postman_environment.json`** - Postman environment variables
4. **`api_docs.html`** - Interactive Swagger UI documentation
5. **`README.md`** - Documentation guide and usage instructions

**Features:**
- 🔄 Automatically fetches OpenAPI spec from running server
- 📁 Organizes endpoints by tags/categories
- 🔑 Pre-configured authentication (Firebase Bearer tokens)
- 🎯 Example requests with realistic data
- 🌐 Interactive HTML documentation with Swagger UI
- 📱 Ready-to-import Postman collection

## 🎯 Use Cases

### Development Workflow
```bash
# 1. Start your server
python main.py

# 2. Run full pipeline to verify everything works
./scripts/run_complete_test.sh --verbose

# 3. Use generated documentation for frontend integration
open docs/api_docs.html
```

### CI/CD Integration
```bash
# In your CI pipeline
./scripts/run_complete_test.sh --base-url $API_URL --skip-docs

# Or just smoke tests for faster feedback
./scripts/run_smoke_tests.sh --base-url $API_URL
```

### API Documentation for Frontend Team
```bash
# Generate docs and share with frontend developers
python scripts/generate_docs.py --base-url https://staging-api.voiceapp.com
# Share the ./docs folder with your team
```

### Production Health Check
```bash
# Quick production API verification
./scripts/run_smoke_tests.sh --base-url https://api.voiceapp.com
```

## 📋 Prerequisites

### Required
- **Python 3.8+**
- **curl** (for server health checks)
- **Running VoiceApp backend** (for most operations)

### Python Dependencies
The scripts will automatically install missing dependencies:
- `aiohttp` - Async HTTP client
- `websockets` - WebSocket client
- `firebase-admin` - Firebase authentication
- `requests` - HTTP requests

### Optional
- **Virtual environment** (recommended)
- **Firebase credentials** (`firebase-credentials.json`)

## 🔧 Configuration

### Environment Setup
```bash
# Recommended: Use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Firebase Configuration
For full testing, place your Firebase credentials file:
```
firebase-credentials.json  # In project root
```

If Firebase is not configured:
- Authentication tests will be skipped
- Other tests will still run

### Server Configuration
Ensure your server exposes:
- Root endpoint: `/` (health check)
- OpenAPI spec: `/openapi.json` (for documentation)
- All API endpoints with proper CORS

## 📊 Output Examples

### Successful Run
```
🔥 VoiceApp Complete Test & Documentation Pipeline
===================================================

🎯 Target API: http://localhost:8000
📁 Docs Output: ./docs
🔍 Verbose: false

============================================
 🔍 Checking Prerequisites
============================================

✅ Running from project root
✅ Python found: Python 3.9.7
✅ Virtual environment detected
✅ All dependencies are installed

============================================
 🔍 Server Health Check
============================================

Testing connection to: http://localhost:8000
✅ Server is responding at http://localhost:8000
📡 Server message: VoiceApp Backend API

============================================
 🔥 Running Smoke Tests
============================================

🚀 Executing smoke tests...
Command: python scripts/smoke_test.py --base-url http://localhost:8000

🔥 Starting VoiceApp Backend Smoke Tests
📡 Testing against: http://localhost:8000
============================================================
✅ Health Check (Root): PASS (0.12s)
✅ Health Check (AI Host): PASS (0.08s)
✅ Firebase User Creation: PASS (0.45s)
✅ User Registration: PASS (0.23s)
✅ User Login: PASS (0.18s)
✅ Get User Profile: PASS (0.15s)
✅ Topic Extraction: PASS (1.34s)
✅ Text-to-Speech: PASS (2.11s)
✅ AI Simple Test: PASS (0.09s)
✅ Room Creation: PASS (0.31s)
✅ Room Details: PASS (0.12s)
✅ Room List: PASS (0.08s)
✅ Room WebSocket: PASS (1.02s)
✅ Traditional Matching: PASS (0.19s)
✅ Matching Status: PASS (0.07s)
✅ AI Matching: PASS (0.76s)
✅ Timeout Statistics: PASS (0.05s)
✅ Cancel Match: PASS (0.04s)
✅ Topics List: PASS (0.06s)
✅ Popular Topics: PASS (0.08s)
✅ Friends List: PASS (0.05s)
============================================================
🏁 Smoke Test Results:
   📊 Total Tests: 20
   ✅ Passed: 20
   ❌ Failed: 0
   ⏭️ Skipped: 0
   ⏱️ Total Time: 7.42s

🎉 Smoke tests completed successfully! (100.0% pass rate)

🎉 Smoke tests completed successfully!

============================================
 📚 Generating API Documentation
============================================

🔧 Generating comprehensive API documentation...
Command: python scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./docs

📚 Generating API documentation...
🎯 Target: http://localhost:8000
📁 Output: ./docs
==================================================
🔍 Fetching OpenAPI spec from http://localhost:8000/openapi.json
✅ OpenAPI specification fetched successfully
🔧 Generating OpenAPI JSON...
✅ OpenAPI JSON saved to: ./docs/openapi.json
🔧 Generating Postman Collection...
✅ Postman collection saved to: ./docs/VoiceApp_API.postman_collection.json
🔧 Generating Postman Environment...
✅ Postman environment saved to: ./docs/VoiceApp_Environment.postman_environment.json
🔧 Generating HTML Documentation...
📝 Generating HTML documentation...
✅ HTML documentation saved to: ./docs/api_docs.html
🌐 Open in browser: file:///Users/user/VoiceApp/docs/api_docs.html
🔧 Generating Documentation README...
✅ Documentation README saved to: ./docs/README.md
==================================================
📊 Documentation Generation Results:
   ✅ Success: 6/6
   📁 Output Directory: /Users/user/VoiceApp/docs

🎉 All documentation generated successfully!
🌐 View docs: file:///Users/user/VoiceApp/docs/api_docs.html

🎉 Documentation generated successfully!
📁 Documentation saved to: /Users/user/VoiceApp/docs
🌐 HTML documentation: file:///Users/user/VoiceApp/docs/api_docs.html

============================================
 📊 Pipeline Summary
============================================

🎯 Target API: http://localhost:8000
📅 Completed at: Fri Dec  1 15:30:45 PST 2023

✅ Smoke Tests: PASSED
✅ Documentation: GENERATED
   📁 Location: /Users/user/VoiceApp/docs

🎉 Pipeline completed successfully!

🚀 Next Steps:
   • Import Postman collection: ./docs/VoiceApp_API.postman_collection.json
   • View API docs: file:///Users/user/VoiceApp/docs/api_docs.html
   • Review frontend integration guide: FRONTEND_API_GUIDE.md
   • Start developing with the API!

🎊 All done! VoiceApp is ready for integration.
```

## 🎯 Next Steps

After running the scripts successfully:

1. **📱 Frontend Integration**
   - Import Postman collection: `docs/VoiceApp_API.postman_collection.json`
   - Review API guide: `FRONTEND_API_GUIDE.md`
   - Use OpenAPI spec: `docs/openapi.json`

2. **🧪 Continuous Testing**
   - Add scripts to your CI/CD pipeline
   - Set up automated testing on commits
   - Monitor API health in production

3. **📚 Documentation Sharing**
   - Share `docs/` folder with frontend team
   - Host HTML docs on internal server
   - Generate client SDKs from OpenAPI spec

4. **🔄 Regular Updates**
   - Re-run scripts after API changes
   - Update documentation with new features
   - Maintain test coverage as API evolves

---

**Happy testing! 🚀** 