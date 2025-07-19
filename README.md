# VoiceApp Backend API 🎙️

**A production-ready API for real-time voice conversations with AI-powered matching.**

> **For Frontend Developers:** This backend provides comprehensive API documentation and ready-to-use integration tools. Everything you need to build amazing voice experiences! 🚀

## 🎯 **What We Provide**

### 🤖 **API Documentation System**
- **📖 Interactive Swagger UI** - Test APIs directly in your browser
- **📬 Postman Collections** - Import and start testing immediately  
- **📋 OpenAPI Specifications** - Generate client SDKs for any language
- **📚 Detailed Integration Guide** - Step-by-step frontend integration instructions

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

### **🌐 View Live API Documentation:**
```bash
# 1. Start the server
python3 main.py

# 2. Open your browser
http://localhost:8000/docs  # Interactive Swagger UI
http://localhost:8000/openapi.json  # OpenAPI spec
```

### **📬 Generate Postman Collection:**
```bash
# Generate fresh documentation
python3 scripts/generate_docs.py --base-url http://localhost:8000 --output-dir ./api-docs

# Import these files into Postman:
- api-docs/VoiceApp_API.postman_collection.json
- api-docs/VoiceApp_Environment.postman_environment.json
```

### **📁 Generated Files Structure:**
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
- **`scripts/README.md`** - Documentation generation scripts

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

# Simple documentation generation
python3 scripts/generate_docs.py --base-url http://localhost:8000
```

## 🎯 **Quick Integration Checklist**

### **For React/Vue/Angular Developers:**
- [ ] Import Postman collection from `api-docs/VoiceApp_API.postman_collection.json`
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
- **Generated Docs**: `./api-docs/` (after running scripts)
- **Postman Collections**: `./api-docs/*.postman_collection.json`

### **🧪 Testing & Validation**
```bash
# Quick API health check
curl http://localhost:8000/

# Generate fresh documentation
python3 scripts/generate_docs.py --base-url http://localhost:8000
```

---

## 🎉 **Start Building Amazing Voice Experiences!**

With our comprehensive documentation and developer-friendly tools, you have everything needed to build incredible voice-powered applications. 

**Happy coding!** 🚀

---

*This README focuses on core functionality and developer experience.*
