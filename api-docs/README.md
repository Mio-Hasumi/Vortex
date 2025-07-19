# VoiceApp API Documentation

Generated on: 2025-07-19 13:57:08
API Base URL: http://localhost:8000

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
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8000/api/auth/profile
   ```

## 📡 WebSocket Endpoints

The API includes several WebSocket endpoints:

- **AI Live Subtitle**: `ws://localhost:8000/api/ai-host/live-subtitle`
- **AI Voice Chat**: `ws://localhost:8000/api/ai-host/voice-chat`
- **Room Communication**: `ws://localhost:8000/api/rooms/ws/{room_id}`
- **Matching Queue**: `ws://localhost:8000/api/matching/ws?user_id={user_id}`
- **General Notifications**: `ws://localhost:8000/api/matching/ws/general?user_id={user_id}`

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
