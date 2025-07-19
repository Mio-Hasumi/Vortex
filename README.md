# VoiceApp Backend API 🎙️

**A fully automated, production-ready API for real-time voice conversations with AI-powered matching and documentation.**

> **For Frontend Developers:** This backend provides comprehensive API documentation, automated testing, and ready-to-use integration tools. Everything you need to build amazing voice experiences is here! 🚀

## 🎯 **What We've Built For You**

### 🤖 **Automated API Documentation System**
We've implemented a complete automated documentation pipeline that generates:
- **📖 Interactive Swagger UI** - Test APIs directly in your browser
- **📬 Postman Collections** - Import and start testing immediately  
- **📋 OpenAPI Specifications** - Generate client SDKs for any language
- **📚 Detailed Integration Guide** - Step-by-step frontend integration instructions

### 🔥 **Continuous Testing & Quality Assurance**
- **Automated Smoke Tests** - Every API endpoint tested on each commit
- **Performance Monitoring** - Response time and load testing
- **Security Scanning** - Automatic vulnerability detection
- **Multi-Environment Support** - Staging and production validation

## 📡 **API Architecture**

```
           Frontend (iOS/Web/Android)
                     ↓
          🚀 VoiceApp FastAPI Backend
                     ↓
    ┌─────────┬─────────┬─────────┬─────────┐
    │Firebase │ Redis   │LiveKit  │OpenAI   │
    │Auth/DB  │Caching  │RTC      │GPT-4o   │
    └─────────┴─────────┴─────────┴─────────┘
```

## 🛠️ **Getting Started for Frontend Developers**

### **Option 1: Use Generated Documentation (Recommended)**

**🌐 View Live API Documentation:**
```bash
# 1. Start the server
python3 main.py

# 2. Open your browser
http://localhost:8000/docs  # Interactive Swagger UI
http://localhost:8000/openapi.json  # OpenAPI spec
```

**📬 Import Postman Collection:**
```bash
# Generate fresh documentation
./scripts/run_complete_test.sh --skip-smoke

# Import these files into Postman:
- docs/VoiceApp_API.postman_collection.json
- docs/VoiceApp_Environment.postman_environment.json
```

### **Option 2: Automated Documentation Generation**

**🔄 Generate Latest Documentation:**
```bash
# Generate all documentation formats
python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./api-docs

# What you get:
✅ Interactive HTML documentation (api_docs.html)
✅ Postman collection (.postman_collection.json)  
✅ Postman environment (.postman_environment.json)
✅ OpenAPI JSON specification (openapi.json)
✅ Integration README with examples
```

**📁 Generated Files Structure:**
```
api-docs/
├── api_docs.html                           # 🌐 Interactive Swagger UI
├── openapi.json                           # 📋 OpenAPI 3.0 specification
├── VoiceApp_API.postman_collection.json   # 📬 Postman collection
├── VoiceApp_Environment.postman_environment.json  # ⚙️ Environment variables
└── README.md                              # 📖 Usage instructions
```

## 🎮 **Key API Features**

### **🔐 Authentication Flow**
```typescript
// Register new user
POST /api/auth/register
// Login existing user  
POST /api/auth/login
// Get user profile
GET /api/auth/profile
```

### **🤖 AI-Powered Services**
```typescript
// Extract topics from text
POST /api/ai-host/extract-topics
// Generate speech from text
POST /api/ai-host/tts
// Start AI conversation session
POST /api/ai-host/start-session
// Real-time voice chat WebSocket
WebSocket /api/ai-host/voice-chat
```

### **🎯 Smart Matching System**
```typescript
// AI-powered user matching
POST /api/matching/ai-match
// Traditional topic matching
POST /api/matching/match
// Check matching status
GET /api/matching/status
```

### **🏠 Room Management**
```typescript
// Create voice room
POST /api/rooms/
// Join existing room
GET /api/rooms/{id}
// List active rooms
GET /api/rooms/
```

### **🎙️ Recording & Transcription**
```typescript
// Get user recordings
GET /api/recordings/
// Download recording file
GET /api/recordings/{id}
// Get AI transcript
GET /api/recordings/{id}/transcript
// Get conversation summary
GET /api/recordings/{id}/summary
```

## 📚 **Frontend Integration Resources**

### **📖 Essential Documentation**
- **`FRONTEND_API_GUIDE.md`** - Complete API integration guide with examples
- **`CI_CD_GUIDE.md`** - Automated testing and deployment setup
- **`scripts/README.md`** - Testing and documentation scripts

### **🔧 Client SDK Generation**
```bash
# Generate TypeScript/JavaScript client
npx @openapitools/openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-axios \
  -o ./src/api

# Generate Swift client for iOS
openapi-generator generate \
  -i http://localhost:8000/openapi.json \
  -g swift5 \
  -o ./VoiceApp/API
```

### **🧪 Testing Your Integration**
```bash
# Test all API endpoints
./scripts/run_smoke_tests.sh

# Generate fresh documentation  
./scripts/run_complete_test.sh

# Docker-based testing
./scripts/docker_test.sh
```

## 🚀 **Automated CI/CD System**

We've implemented comprehensive CI/CD automation:

### **✅ Continuous Testing**
- Every commit triggers automatic API testing
- Performance benchmarks on all endpoints
- Security vulnerability scanning
- Documentation freshness validation

### **📚 Automated Documentation**
- OpenAPI specs updated on every release
- Postman collections auto-generated
- Interactive documentation deployed
- Frontend integration examples maintained

### **🌐 Multi-Platform CI/CD**
- **GitHub Actions** - Automatic PR testing and documentation deployment
- **GitLab CI/CD** - Docker-based testing with GitLab Pages
- **Jenkins** - Enterprise CI/CD with Slack notifications
- **Docker** - Containerized testing for consistency

## 🎯 **Quick Integration Checklist**

### **For React/Vue/Angular Developers:**
- [ ] Import Postman collection from `docs/VoiceApp_API.postman_collection.json`
- [ ] Generate TypeScript client from OpenAPI spec
- [ ] Review authentication flow in `FRONTEND_API_GUIDE.md`
- [ ] Test WebSocket connections for real-time features
- [ ] Implement Firebase authentication integration

### **For iOS/Swift Developers:**
- [ ] Generate Swift client from OpenAPI specification
- [ ] Configure Firebase authentication
- [ ] Implement WebSocket for real-time voice features
- [ ] Test audio recording and playback integration
- [ ] Review voice permission handling

### **For Flutter/React Native Developers:**
- [ ] Generate Dart/JavaScript client from OpenAPI spec
- [ ] Configure cross-platform authentication
- [ ] Implement WebSocket real-time communication
- [ ] Test voice recording capabilities
- [ ] Handle platform-specific audio permissions

## 🛡️ **Security & Best Practices**

### **🔐 Authentication**
- Firebase ID tokens for secure authentication
- JWT-based session management
- Automatic token refresh handling
- Secure WebSocket authentication

### **🌐 API Standards**
- RESTful API design principles
- OpenAPI 3.0 specification compliance
- Consistent error response formatting
- Rate limiting and request validation

### **🔒 Data Protection**
- HTTPS-only communication
- Audio data encryption in transit
- User privacy controls
- GDPR compliance ready

## 📞 **Need Help?**

### **📖 Documentation Locations**
- **Live API Docs**: `http://localhost:8000/docs`
- **Integration Guide**: `FRONTEND_API_GUIDE.md`
- **Generated Docs**: `./docs/` (after running scripts)
- **Postman Collections**: `./docs/*.postman_collection.json`

### **🧪 Testing & Validation**
```bash
# Quick API health check
curl http://localhost:8000/

# Full API testing suite
./scripts/run_complete_test.sh

# Generate fresh documentation
python3 scripts/generate_docs.py --base-url http://localhost:8000
```

### **🚀 Ready to Deploy**
Our automated CI/CD system ensures:
- ✅ All APIs tested and validated
- ✅ Documentation always up-to-date
- ✅ Performance benchmarks maintained
- ✅ Security vulnerabilities detected
- ✅ Multi-environment deployment ready

---

## 🎉 **Start Building Amazing Voice Experiences!**

With our automated documentation, comprehensive testing, and developer-friendly tools, you have everything needed to build incredible voice-powered applications. 

**Happy coding!** 🚀

---

*This README is automatically updated by our CI/CD pipeline. Last updated: $(date)*
