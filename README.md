
```
Frontend (React/Vue/React Native)
           ↓
    FastAPI Backend + WebSockets
           ↓
┌─────────┬─────────┬─────────┬─────────┐
│Firebase │ Redis   │LiveKit  │OpenAI   │
│Auth/DB  │Caching  │RTC      │GPT-4o   │
└─────────┴─────────┴─────────┴─────────┘
```

## 📡 **API Overview**

### **🔐 Authentication**
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile

### **🤖 AI Host Services**
- `POST /api/ai-host/start-session` - Start AI conversation
- `POST /api/ai-host/extract-topics` - Extract topics from text
- `POST /api/ai-host/tts` - Text-to-speech generation
- `POST /api/ai-host/upload-audio` - Voice input processing
- `WebSocket /api/ai-host/voice-chat` - Real-time AI conversation
- `WebSocket /api/ai-host/live-subtitle` - Live transcription

### **🎯 Matching System**
- `POST /api/matching/ai-match` - AI-powered user matching
- `POST /api/matching/match` - Traditional topic-based matching
- `GET /api/matching/status` - Check matching status
- `POST /api/matching/cancel` - Cancel current match

### **🏠 Room Management**
- `GET /api/rooms/` - List active rooms
- `POST /api/rooms/` - Create new room
- `GET /api/rooms/{id}` - Get room details

### **🎙️ Recordings**
- `GET /api/recordings/` - List user recordings
- `GET /api/recordings/{id}` - Download recording
- `GET /api/recordings/{id}/transcript` - Get conversation transcript
- `GET /api/recordings/{id}/summary` - Get AI-generated summary

### **👥 Friends & Social**
- `GET /api/friends/` - List friends
- `POST /api/friends/add` - Send friend request
- `GET /api/friends/requests` - Manage friend requests
- `GET /api/friends/search` - Search users

### **🏷️ Topics**
- `GET /api/topics/` - List all topics
- `GET /api/topics/popular` - Get trending topics
- `GET /api/topics/search` - Search topics by keywords

## 🎮 **Complete User Flow**

```mermaid
graph TD
    A[User Opens App] --> B[Register/Login]
    B --> C[Voice Input: "I want to talk about AI"]
    C --> D[AI Extracts Topics & Hashtags]
    D --> E[Smart Matching Algorithm]
    E --> F{Match Found?}
    F -->|Yes| G[Create Voice Room]
    F -->|No| H[Wait in Queue]
    H --> F
    G --> I[AI Host Introduction]
    I --> J[Real-time Voice Chat + Subtitles]
    J --> K[AI Assistant Available On-Demand]
    K --> L[Call Ends]
    L --> M[Add Friend Option]
    L --> N[Download Recording & Transcript]
```

### **Project Structure**
```
VoiceApp-martin/
├── api/                    # API route handlers
│   └── routers/           # Organized by feature
├── domain/                # Business logic & entities
├── infrastructure/        # External service integrations
│   ├── ai/               # OpenAI & AI services
│   ├── auth/             # Firebase authentication
│   ├── db/               # Database connections
│   └── repositories/     # Data access layer
├── usecase/              # Business use cases
└── main.py              # Application entry point
```

This project is licensed under the MIT License.