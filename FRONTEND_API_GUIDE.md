# VoiceApp Frontend API Guide

**Complete API Reference for VoiceApp - AI-Powered Voice Social Platform**

This comprehensive guide provides everything frontend developers need to integrate with the VoiceApp backend, featuring GPT-4o Audio, real-time matching, and voice chat capabilities.

## 🌐 Base Configuration

### Base URLs
```javascript
const API_BASE_URL = 'https://your-app.up.railway.app'
const WS_BASE_URL = 'wss://your-app.up.railway.app'
```

### Authentication Headers
All protected endpoints require Firebase ID Token:
```javascript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${firebaseIdToken}`
}
```

## 🔐 Authentication API (`/api/auth`)

### Register User
```javascript
POST /api/auth/register
Headers: { Content-Type: "application/json" }
{
  "firebase_uid": "string",
  "email": "user@example.com", 
  "display_name": "John Doe"
}

// Response
{
  "user_id": "uuid",
  "display_name": "John Doe",
  "email": "user@example.com",
  "message": "User registered successfully"
}
```

### Login User
```javascript
POST /api/auth/login
Headers: { Content-Type: "application/json" }
{
  "firebase_uid": "string",
  "email": "user@example.com"
}

// Response
{
  "user_id": "uuid",
  "display_name": "John Doe", 
  "email": "user@example.com",
  "message": "User authenticated successfully"
}
```

### Sign Out
```javascript
POST /api/auth/signout
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Get User Profile
```javascript
GET /api/auth/profile
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "id": "uuid",
  "display_name": "John Doe",
  "email": "user@example.com",
  "profile_image_url": "string",
  "bio": "string",
  "status": "online",
  "firebase_uid": "string",
  "last_seen": "2023-12-01T10:00:00Z",
  "created_at": "2023-11-01T08:00:00Z",
  "is_active": true,
  "preferred_language": "en",
  "topic_preferences": ["ai", "technology"],
  "interest_levels": {"ai": 5, "technology": 4}
}
```

## 🤖 AI Host Services (`/api/ai-host`)

### Health Check
```javascript
GET /api/ai-host/health

// Response
{
  "status": "healthy",
  "openai_available": true,
  "features": ["tts", "stt", "topic_extraction", "conversation_ai"],
  "timestamp": "2023-12-01T10:00:00Z"
}
```

### Start AI Session
```javascript
POST /api/ai-host/start-session
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "user_preferences": {
    "conversation_style": "casual", // casual, formal, educational
    "topics_of_interest": ["ai", "technology"],
    "language": "en-US"
  },
  "language": "en-US",
  "voice": "nova" // alloy, echo, fable, onyx, nova, shimmer
}

// Response
{
  "session_id": "uuid",
  "ai_greeting": "Hi! Welcome to VoiceApp! What would you like to discuss today?",
  "session_state": "active",
  "available_features": ["voice_input", "text_input", "topic_suggestions"],
  "created_at": "2023-12-01T10:00:00Z"
}
```

### Process User Input
```javascript
POST /api/ai-host/process-input
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "session_id": "uuid",
  "user_input": "I want to talk about artificial intelligence and its impact on society"
}

// Response
{
  "session_id": "uuid",
  "ai_response": "That's a fascinating topic! AI is transforming many aspects of our daily lives...",
  "session_state": "active",
  "extracted_topics": ["artificial intelligence", "society", "technology"],
  "generated_hashtags": ["#AI", "#Technology", "#Society", "#FutureTech"],
  "next_action": "continue_conversation" // continue_conversation, suggest_topics, end_session
}
```

### Text-to-Speech (TTS)
```javascript
// POST method (Recommended)
POST /api/ai-host/tts
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "text": "Hello, welcome to VoiceApp!",
  "voice": "nova",  // alloy, echo, fable, onyx, nova, shimmer
  "speed": 1.0      // 0.25 to 4.0
}

// Returns: MP3 audio stream
// Content-Type: audio/mpeg

// GET method (Simple use)
GET /api/ai-host/tts/{text}?voice=nova&speed=1.0
Headers: { Authorization: "Bearer <firebase_token>" }

// Example usage in JavaScript
const playTTS = async (text, voice = 'nova') => {
  const response = await fetch('/api/ai-host/tts', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ text, voice })
  })
  
  const audioBlob = await response.blob()
  const audioUrl = URL.createObjectURL(audioBlob)
  const audio = new Audio(audioUrl)
  await audio.play()
}
```

### Extract Topics from Text
```javascript
POST /api/ai-host/extract-topics
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "text": "I'm really interested in machine learning, especially neural networks and deep learning applications in computer vision.",
  "user_context": {
    "previous_topics": ["ai", "programming"],
    "expertise_level": "intermediate"
  }
}

// Response
{
  "main_topics": ["machine learning", "neural networks", "deep learning", "computer vision"],
  "hashtags": ["#MachineLearning", "#NeuralNetworks", "#DeepLearning", "#ComputerVision", "#AI"],
  "category": "Technology",
  "sentiment": "positive",
  "confidence": 0.95,
  "conversation_style": "technical",
  "suggested_follow_up": "Would you like to discuss specific applications of computer vision?"
}
```

### Extract Topics from Voice
```javascript
POST /api/ai-host/extract-topics-from-voice
Headers: { Authorization: "Bearer <firebase_token>" }
Content-Type: multipart/form-data

FormData:
- audio_file: File (max 25MB, audio format)
- language: "en-US" (optional)

// Response
{
  "transcription": "I want to discuss artificial intelligence and machine learning",
  "main_topics": ["artificial intelligence", "machine learning"],
  "hashtags": ["#AI", "#MachineLearning", "#Technology"],
  "category": "Technology", 
  "sentiment": "neutral",
  "confidence": 0.92,
  "language_detected": "en-US",
  "audio_duration": 3.5,
  "processing_time": 1.2
}
```

### Upload Audio for Speech-to-Text
```javascript
POST /api/ai-host/upload-audio
Headers: { Authorization: "Bearer <firebase_token>" }
Content-Type: multipart/form-data

FormData:
- audio_file: File (max 25MB)
- language: "en-US" (optional)

// Response
{
  "transcription": "Hello, I want to join a conversation about technology",
  "language": "en-US",
  "confidence": 0.95,
  "duration": 4.2,
  "segments": [
    {
      "text": "Hello, I want to join a conversation",
      "start": 0.0,
      "end": 2.1
    },
    {
      "text": "about technology",
      "start": 2.1,
      "end": 4.2
    }
  ]
}
```

### Test Simple Endpoint
```javascript
GET /api/ai-host/test-simple
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "message": "AI Host service is working",
  "timestamp": "2023-12-01T10:00:00Z",
  "features": ["tts", "stt", "topic_extraction"]
}
```

## 🎯 Matching System (`/api/matching`)

### Request Match
```javascript
POST /api/matching/match
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "preferred_topics": ["ai", "technology", "programming"],
  "max_participants": 3,
  "language_preference": "en-US"
}

// Response
{
  "match_id": "uuid",
  "room_id": "uuid", // Empty if not matched yet
  "participants": ["uuid"], // Initially just the requester
  "topic": "ai",
  "status": "pending", // pending, matched, cancelled
  "estimated_wait_time": 30 // seconds
}
```

### AI-Driven Match (NEW)
```javascript
POST /api/matching/ai-match  
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "voice_input": "base64_audio_data", // Optional: voice description
  "text_input": "I want to discuss AI and startups", // Optional: text description
  "conversation_style": "casual", // casual, formal, educational, debate
  "language": "en-US",
  "max_participants": 3
}

// Response
{
  "match_id": "uuid",
  "ai_analysis": {
    "extracted_topics": ["ai", "startups", "entrepreneurship"],
    "generated_hashtags": ["#AI", "#Startups", "#Tech", "#Entrepreneurship"],
    "conversation_style": "casual",
    "interest_level": "high"
  },
  "matching_criteria": {
    "primary_topics": ["ai", "startups"],
    "secondary_topics": ["technology", "business"],
    "style_compatibility": ["casual", "educational"]
  },
  "status": "searching", // searching, matched, failed
  "estimated_wait_time": 45,
  "ai_voice_confirmation": "base64_audio_data" // TTS confirmation
}
```

### Cancel Match
```javascript
POST /api/matching/cancel
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Get Match Status
```javascript
GET /api/matching/status
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "status": "searching", // searching, matched, not_searching
  "match_id": "uuid",
  "queue_position": 3,
  "estimated_wait_time": 45,
  "topics": ["ai", "technology"],
  "participants_found": 1,
  "max_participants": 3,
  "time_in_queue": 120 // seconds
}
```

### Get Match History
```javascript
GET /api/matching/history?limit=20&offset=0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "matches": [
    {
      "match_id": "uuid",
      "room_id": "uuid", 
      "topic": "ai",
      "participants": ["uuid1", "uuid2"],
      "status": "completed",
      "created_at": "2023-12-01T10:00:00Z",
      "duration": 1800 // seconds
    }
  ],
  "total": 15
}
```

### Process Timeout Matches (Admin)
```javascript
POST /api/matching/process-timeout-matches
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "timeout_minutes": 2.0,
  "force_process": false
}

// Response
{
  "processed": true,
  "timeout_users_count": 5,
  "matches_created": 2,
  "remaining_users": 1,
  "processing_time": 1.2
}
```

### Get Timeout Statistics
```javascript
GET /api/matching/timeout-stats?timeout_minutes=2.0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "total_queue_size": 10,
  "timeout_users_count": 3,
  "timeout_minutes": 2.0,
  "timeout_percentage": 30.0,
  "ready_for_timeout_matching": true,
  "average_wait_time": 180.5,
  "queue_health": "normal" // normal, degraded, critical
}
```

## 🏠 Room Management (`/api/rooms`)

### Create Room
```javascript
POST /api/rooms/
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "name": "AI Discussion Room",
  "topic": "artificial intelligence", // Can be string or topic ID
  "max_participants": 5,
  "is_private": false
}

// Response
{
  "id": "uuid",
  "name": "AI Discussion Room", 
  "topic": "artificial intelligence",
  "participants": ["uuid"], // Creator initially
  "max_participants": 5,
  "status": "active",
  "created_at": "2023-12-01T10:00:00Z",
  "livekit_room_name": "room_uuid_timestamp",
  "livekit_token": "jwt_token_here"
}
```

### Join Room
```javascript
POST /api/rooms/join
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "room_id": "uuid"
}

// Response
{
  "id": "uuid",
  "name": "AI Discussion Room",
  "topic": "artificial intelligence", 
  "participants": ["uuid1", "uuid2"], // Updated participant list
  "max_participants": 5,
  "status": "active",
  "created_at": "2023-12-01T10:00:00Z", 
  "livekit_room_name": "room_uuid_timestamp",
  "livekit_token": "jwt_token_for_new_participant"
}
```

### Leave Room
```javascript
POST /api/rooms/{room_id}/leave
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Get Room Details
```javascript
GET /api/rooms/{room_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "id": "uuid",
  "name": "AI Discussion Room",
  "topic": "artificial intelligence",
  "participants": ["uuid1", "uuid2"],
  "max_participants": 5,
  "status": "active", // active, paused, ended
  "created_at": "2023-12-01T10:00:00Z",
  "livekit_room_name": "room_uuid_timestamp",
  "livekit_token": "jwt_token_here",
  "description": "Room for AI discussions",
  "is_private": false,
  "created_by": "uuid"
}
```

### Get Room Participants
```javascript
GET /api/rooms/{room_id}/participants
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
[
  {
    "user_id": "uuid",
    "display_name": "John Doe",
    "joined_at": "2023-12-01T10:00:00Z",
    "is_speaking": false,
    "is_muted": false,
    "role": "participant" // participant, moderator, creator
  }
]
```

### List Rooms
```javascript
GET /api/rooms/?status=active&topic=ai&limit=20&offset=0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "rooms": [
    {
      "id": "uuid",
      "name": "AI Discussion Room",
      "topic": "artificial intelligence",
      "participants": ["uuid1", "uuid2"],
      "max_participants": 5,
      "status": "active",
      "created_at": "2023-12-01T10:00:00Z",
      "livekit_room_name": "room_uuid_timestamp",
      "livekit_token": "jwt_token_here"
    }
  ],
  "total": 1
}
```

## 🎙️ Recordings (`/api/recordings`)

### List User Recordings
```javascript
GET /api/recordings/?room_id=uuid&topic=ai&limit=20&offset=0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "recordings": [
    {
      "id": "uuid",
      "room_id": "uuid",
      "room_name": "AI Discussion Room",
      "topic": "artificial intelligence",
      "participants": ["uuid1", "uuid2"],
      "duration": 1800, // seconds
      "file_size": 15728640, // bytes
      "created_at": "2023-12-01T10:00:00Z",
      "status": "ready", // processing, ready, failed
      "download_url": "https://storage.url/recording.mp3"
    }
  ],
  "total": 1
}
```

### Get Recording Details
```javascript
GET /api/recordings/{recording_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "id": "uuid",
  "room_id": "uuid",
  "room_name": "AI Discussion Room",
  "topic": "artificial intelligence",
  "participants": ["uuid1", "uuid2"],
  "duration": 1800,
  "file_size": 15728640,
  "created_at": "2023-12-01T10:00:00Z",
  "status": "ready",
  "download_url": "https://storage.url/recording.mp3",
  "metadata": {
    "audio_quality": "high",
    "format": "mp3",
    "bitrate": "128kbps"
  }
}
```

### Download Recording
```javascript
GET /api/recordings/{recording_id}/download
Headers: { Authorization: "Bearer <firebase_token>" }

// Returns audio file stream
// Content-Type: audio/mpeg
// Content-Disposition: attachment; filename="recording.mp3"
```

### Update Recording Metadata
```javascript
POST /api/recordings/{recording_id}/metadata
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "title": "Great AI Discussion",
  "description": "Discussion about AI and future technology",
  "tags": ["ai", "technology", "future"]
}

// Response
{
  "id": "uuid",
  "title": "Great AI Discussion",
  "description": "Discussion about AI and future technology", 
  "tags": ["ai", "technology", "future"],
  "updated_at": "2023-12-01T11:00:00Z"
}
```

### Delete Recording
```javascript
DELETE /api/recordings/{recording_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Share Recording
```javascript
POST /api/recordings/{recording_id}/share
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "share_type": "public", // public, friends, private
  "expiry_hours": 24 // Optional, default 24
}

// Response
{
  "share_url": "https://app.com/shared/recording/abc123",
  "share_type": "public",
  "expires_at": "2023-12-02T10:00:00Z",
  "share_id": "abc123"
}
```

### Get Recording Transcript
```javascript
GET /api/recordings/{recording_id}/transcript
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "recording_id": "uuid",
  "transcript": [
    {
      "speaker": "uuid1",
      "speaker_name": "John Doe", 
      "text": "Hello everyone, let's discuss AI",
      "start_time": 0.0,
      "end_time": 3.2,
      "confidence": 0.95
    },
    {
      "speaker": "uuid2",
      "speaker_name": "Jane Smith",
      "text": "That's a great topic!",
      "start_time": 3.5,
      "end_time": 5.1,
      "confidence": 0.92
    }
  ],
  "summary": "Discussion about artificial intelligence and its applications",
  "key_topics": ["ai", "technology", "future"],
  "total_duration": 1800,
  "language": "en-US"
}
```

### Get AI-Generated Summary
```javascript
GET /api/recordings/{recording_id}/summary
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "recording_id": "uuid",
  "summary": {
    "brief": "The conversation covered AI fundamentals, machine learning applications, and future implications for society.",
    "key_points": [
      "Discussion of neural networks and deep learning",
      "Applications in healthcare and finance",
      "Ethical considerations in AI development",
      "Future predictions for AI technology"
    ],
    "main_topics": ["artificial intelligence", "machine learning", "ethics", "future technology"],
    "participants_summary": {
      "uuid1": "Contributed insights on technical aspects of AI",
      "uuid2": "Focused on ethical implications and societal impact"
    },
    "sentiment": "positive",
    "engagement_level": "high"
  },
  "generated_at": "2023-12-01T11:00:00Z",
  "ai_model": "gpt-4"
}
```

## 👥 Friends & Social (`/api/friends`)

### List Friends
```javascript
GET /api/friends/?status=online&limit=50&offset=0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "friends": [
    {
      "user_id": "uuid",
      "display_name": "John Smith",
      "status": "online", // online, offline, in_call
      "last_seen": "2023-12-01T10:00:00Z",
      "friendship_status": "accepted" // pending, accepted, blocked
    }
  ],
  "total": 1
}
```

### Send Friend Request
```javascript
POST /api/friends/request
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "user_id": "uuid"
}

// Response
{
  "friendship_id": "uuid",
  "to_user": "uuid",
  "status": "pending",
  "created_at": "2023-12-01T10:00:00Z"
}
```

### Get Friend Requests
```javascript
GET /api/friends/requests
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "incoming_requests": [
    {
      "friendship_id": "uuid",
      "from_user": {
        "user_id": "uuid",
        "display_name": "John Smith",
        "profile_image_url": "string"
      },
      "created_at": "2023-12-01T10:00:00Z"
    }
  ],
  "outgoing_requests": [
    {
      "friendship_id": "uuid", 
      "to_user": {
        "user_id": "uuid",
        "display_name": "Jane Doe",
        "profile_image_url": "string"
      },
      "created_at": "2023-12-01T09:00:00Z"
    }
  ]
}
```

### Accept Friend Request
```javascript
POST /api/friends/requests/{request_id}/accept
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "friendship_id": "uuid",
  "status": "accepted",
  "accepted_at": "2023-12-01T10:00:00Z"
}
```

### Reject Friend Request
```javascript
POST /api/friends/requests/{request_id}/reject
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "friendship_id": "uuid",
  "status": "rejected",
  "rejected_at": "2023-12-01T10:00:00Z"
}
```

### Remove Friend
```javascript
DELETE /api/friends/{user_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Block User
```javascript
POST /api/friends/{user_id}/block
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "user_id": "uuid",
  "status": "blocked",
  "blocked_at": "2023-12-01T10:00:00Z"
}
```

### Unblock User
```javascript
DELETE /api/friends/{user_id}/block
Headers: { Authorization: "Bearer <firebase_token>" }

// Response: 204 No Content
```

### Search Users
```javascript
GET /api/friends/search?q=john&limit=20
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "users": [
    {
      "user_id": "uuid",
      "display_name": "John Doe",
      "profile_image_url": "string",
      "bio": "AI enthusiast",
      "status": "online",
      "friendship_status": "none" // none, pending, friends, blocked
    }
  ],
  "total": 1
}
```

## 🏷️ Topics (`/api/topics`)

### List All Topics
```javascript
GET /api/topics/?category=technology&difficulty_level=3&limit=50&offset=0

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "Artificial Intelligence",
      "description": "Discussions about AI technology and applications",
      "category": "Technology",
      "difficulty_level": 3, // 1-5 scale
      "is_active": true
    }
  ],
  "total": 1
}
```

### Get Popular Topics
```javascript
GET /api/topics/popular?limit=20
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "AI",
      "participant_count": 150,
      "trend_score": 0.95,
      "category": "Technology",
      "growth_rate": 0.15 // 15% growth
    }
  ]
}
```

### Search Topics
```javascript
GET /api/topics/search?q=technology&limit=20
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "Technology",
      "description": "General technology discussions",
      "relevance_score": 0.98,
      "category": "Technology",
      "participant_count": 200
    }
  ]
}
```

### Get Topic Details
```javascript
GET /api/topics/{topic_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "id": "uuid",
  "name": "Artificial Intelligence",
  "description": "Discussions about AI technology and applications",
  "category": "Technology", 
  "difficulty_level": 3,
  "is_active": true,
  "created_at": "2023-11-01T08:00:00Z",
  "tags": ["ai", "machine-learning", "technology"],
  "participant_count": 150,
  "recent_activity": "high"
}
```

### Set Topic Preferences
```javascript
POST /api/topics/preferences
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "preferred_topics": ["uuid1", "uuid2", "uuid3"],
  "interest_levels": {
    "uuid1": 5, // 1-5 scale
    "uuid2": 4,
    "uuid3": 3
  }
}

// Response
{
  "preferences_updated": true,
  "preferred_topics": ["uuid1", "uuid2", "uuid3"],
  "interest_levels": {
    "uuid1": 5,
    "uuid2": 4, 
    "uuid3": 3
  },
  "updated_at": "2023-12-01T10:00:00Z"
}
```

### Get User Topic Preferences
```javascript
GET /api/topics/preferences
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "preferred_topics": [
    {
      "topic_id": "uuid1",
      "topic_name": "Artificial Intelligence",
      "interest_level": 5,
      "category": "Technology"
    }
  ],
  "interest_levels": {
    "uuid1": 5,
    "uuid2": 4,
    "uuid3": 3
  },
  "last_updated": "2023-12-01T10:00:00Z"
}
```

## 🌐 WebSocket Connections

### AI Live Subtitle WebSocket
```javascript
// Connect to live subtitle service
const subtitleWs = new WebSocket('wss://your-app.up.railway.app/api/ai-host/live-subtitle')

subtitleWs.onopen = () => {
  console.log('🎬 Live subtitle WebSocket connected')
}

subtitleWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'connected':
      console.log('✅ Live subtitle service ready')
      break
    case 'subtitle':
      console.log('📝 Subtitle:', data.text)
      displaySubtitle(data.text, data.timestamp)
      break
    case 'error':
      console.error('❌ Subtitle error:', data.message)
      break
  }
}

// Send text for subtitle generation
subtitleWs.send(JSON.stringify({
  type: 'text',
  text: 'Hello everyone, welcome to the discussion'
}))

// Send audio for real-time STT + subtitle
subtitleWs.send(JSON.stringify({
  type: 'audio',
  audio_data: base64AudioData, // base64 encoded audio
  language: 'en-US'
}))

// Send ping to keep connection alive
setInterval(() => {
  subtitleWs.send(JSON.stringify({ type: 'ping' }))
}, 30000)
```

### AI Voice Chat WebSocket
```javascript
// Connect to AI voice chat
const voiceChatWs = new WebSocket('wss://your-app.up.railway.app/api/ai-host/voice-chat')

voiceChatWs.onopen = () => {
  console.log('🎤 AI voice chat WebSocket connected')
  
  // Start session
  voiceChatWs.send(JSON.stringify({
    type: 'start_session',
    user_id: 'your-user-uuid'
  }))
}

voiceChatWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'connected':
      console.log('🤖 AI greeting:', data.ai_greeting)
      // Play AI greeting TTS
      playAIGreeting(data.ai_greeting)
      break
      
    case 'session_started':
      console.log('🎯 Session started:', data.session_id)
      sessionId = data.session_id
      break
      
    case 'ai_response':
      console.log('🤖 AI response:', data.text)
      // Display response and play TTS if available
      displayMessage(data.text, 'ai')
      break
      
    case 'error':
      console.error('❌ Voice chat error:', data.message)
      break
  }
}

// Send user input to AI
const sendUserInput = (text) => {
  voiceChatWs.send(JSON.stringify({
    type: 'user_input',
    text: text
  }))
}

// Send voice input (base64 encoded audio)
const sendVoiceInput = (audioData) => {
  voiceChatWs.send(JSON.stringify({
    type: 'voice_input',
    audio_data: audioData,
    language: 'en-US'
  }))
}
```

### Room Communication WebSocket
```javascript
// Connect to room for real-time conversation
const roomWs = new WebSocket(
  `wss://your-app.up.railway.app/api/rooms/ws/${roomId}?livekit_name=${livekitRoomName}&user_id=${userId}`
)

roomWs.onopen = () => {
  console.log('🏠 Connected to room WebSocket')
}

roomWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'room_joined':
      console.log('✅ Successfully joined room:', data.room_id)
      console.log('👥 Participants:', data.participants)
      console.log('🤖 AI enabled:', data.ai_enabled)
      console.log('🎛️ Features:', data.supported_features)
      break
      
    case 'user_joined':
      console.log('👋 User joined:', data.user.display_name)
      updateParticipantsList(data.participants)
      break
      
    case 'user_left':
      console.log('👋 User left:', data.user.display_name)
      updateParticipantsList(data.participants)
      break
      
    case 'voice_message':
      console.log('🎙️ Voice message from:', data.user_id)
      playVoiceMessage(data.audio_data)
      break
      
    case 'text_message':
      console.log('💬 Text message:', data.message)
      displayMessage(data.message, data.user_id)
      break
      
    case 'ai_response':
      console.log('🤖 AI moderator:', data.response)
      displayAIResponse(data.response, data.audio_data)
      break
      
    case 'conversation_suggestion':
      console.log('💡 AI suggestion:', data.suggestion)
      showConversationSuggestion(data.suggestion)
      break
      
    case 'error':
      console.error('❌ Room error:', data.error)
      break
  }
}

// Send text message to room
roomWs.send(JSON.stringify({
  type: 'text_message',
  message: 'Hello everyone!',
  user_id: userId
}))

// Send voice message to room
roomWs.send(JSON.stringify({
  type: 'voice_message',
  audio_data: base64AudioData,
  user_id: userId
}))

// Request AI assistance
roomWs.send(JSON.stringify({
  type: 'request_ai_assistance',
  request: 'Can you suggest some topics related to our current discussion?',
  user_id: userId
}))

// Handle conversation pause (AI will suggest topics)
roomWs.send(JSON.stringify({
  type: 'conversation_pause',
  duration: 30 // seconds of silence
}))
```

### Matching Queue WebSocket
```javascript
// Connect to matching queue for real-time updates
const matchingWs = new WebSocket(
  `wss://your-app.up.railway.app/api/matching/ws?user_id=${userId}`
)

matchingWs.onopen = () => {
  console.log('🎯 Connected to matching WebSocket')
}

matchingWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'queue_joined':
      console.log('📋 Joined matching queue')
      updateMatchingStatus('searching')
      break
      
    case 'queue_position_update':
      console.log('📍 Queue position:', data.position)
      console.log('⏱️ Estimated wait:', data.estimated_wait, 'seconds')
      updateQueuePosition(data.position, data.estimated_wait)
      break
      
    case 'match_found':
      console.log('🎉 Match found!')
      console.log('🏠 Room ID:', data.room_id)
      console.log('👥 Partner ID:', data.partner_id)
      console.log('🏷️ Topic:', data.topic)
      redirectToRoom(data.room_id, data.livekit_token)
      break
      
    case 'ai_match_found':
      console.log('🤖 AI match found!')
      console.log('🧠 AI analysis:', data.ai_analysis)
      console.log('🎭 Compatibility score:', data.compatibility_score)
      redirectToRoom(data.room_id, data.livekit_token)
      break
      
    case 'timeout_match_found':
      console.log('⏰ Timeout match found!')
      console.log('⏱️ You waited:', data.wait_time, 'seconds')
      console.log('🔄 Match type:', data.match_type) // "timeout_fallback"
      showNotification(
        'Match Found!', 
        `We found you a conversation partner after ${data.wait_time}s of waiting.`
      )
      redirectToRoom(data.room_id, data.livekit_token)
      break
      
    case 'queue_stats':
      console.log('📊 Queue stats:', data.total_users_in_queue)
      console.log('⏰ Timeout users:', data.timeout_users_count)
      updateQueueStats(data)
      break
      
    case 'match_cancelled':
      console.log('❌ Match cancelled')
      updateMatchingStatus('not_searching')
      break
      
    case 'error':
      console.error('❌ Matching error:', data.message)
      break
      
    case 'pong':
      console.log('🏓 Connection alive')
      break
  }
}

// Send ping to keep connection alive
setInterval(() => {
  matchingWs.send(JSON.stringify({ type: 'ping' }))
}, 30000)
```

### General Notifications WebSocket
```javascript
// Connect to general notifications
const generalWs = new WebSocket(
  `wss://your-app.up.railway.app/api/matching/ws/general?user_id=${userId}`
)

generalWs.onopen = () => {
  console.log('🔔 Connected to notifications WebSocket')
}

generalWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'friend_request':
      console.log('👋 New friend request from:', data.from_user.display_name)
      showNotification('Friend Request', `${data.from_user.display_name} wants to be friends`)
      updateFriendRequestsBadge(data.count)
      break
      
    case 'friend_request_accepted':
      console.log('✅ Friend request accepted by:', data.user.display_name)
      showNotification('Friend Added', `${data.user.display_name} accepted your friend request`)
      break
      
    case 'match_invitation':
      console.log('🎯 Match invitation to room:', data.room_id)
      showMatchInvitation(data)
      break
      
    case 'room_invitation':
      console.log('🏠 Room invitation:', data.room_name)
      showRoomInvitation(data)
      break
      
    case 'system_notification':
      console.log('📢 System message:', data.message)
      showSystemNotification(data.message, data.priority)
      break
      
    case 'user_status_update':
      console.log('👤 User status update:', data.user_id, data.status)
      updateUserStatus(data.user_id, data.status)
      break
      
    case 'pong':
      // Connection alive response
      break
      
    case 'error':
      console.error('❌ Notification error:', data.message)
      break
  }
}

// Send ping heartbeat
setInterval(() => {
  generalWs.send(JSON.stringify({ type: 'ping' }))
}, 30000)
```

## 🚨 Error Handling

### Standard Error Responses
All endpoints return errors in this format:
```javascript
// 400 Bad Request
{
  "detail": "Invalid input data"
}

// 401 Unauthorized  
{
  "detail": "Invalid or expired Firebase token"
}

// 403 Forbidden
{
  "detail": "Access denied to this resource"
}

// 404 Not Found
{
  "detail": "Resource not found"
}

// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}

// 503 Service Unavailable
{
  "detail": "OpenAI service not available"
}
```

### Frontend Error Handling Best Practices
```javascript
const handleApiCall = async (url, options = {}) => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${getFirebaseToken()}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    })

    if (!response.ok) {
      const errorData = await response.json()
      
      switch (response.status) {
        case 401:
          // Token expired, refresh Firebase token
          await refreshFirebaseToken()
          // Retry the request
          return handleApiCall(url, options)
          
        case 403:
          showError('Access denied to this resource')
          break
          
        case 404:
          showError('Resource not found')
          break
          
        case 422:
          // Validation errors
          const validationErrors = errorData.detail
          showValidationErrors(validationErrors)
          break
          
        case 503:
          showError('Service temporarily unavailable. Please try again later.')
          break
          
        default:
          showError('An unexpected error occurred')
      }
      
      throw new Error(`API Error: ${response.status}`)
    }

    return await response.json()
    
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      showError('Network error. Please check your connection.')
    }
    throw error
  }
}
```

## 🎛️ Rate Limiting

### Current Rate Limits
- **Authentication**: 100 requests per minute per IP
- **AI Services**: 50 requests per minute per user
- **WebSocket connections**: 10 concurrent connections per user
- **File uploads**: 5 uploads per minute per user (max 25MB each)
- **General API**: 1000 requests per hour per user

### Rate Limit Headers
```javascript
// Response headers for rate limiting info
{
  "X-RateLimit-Limit": "100",
  "X-RateLimit-Remaining": "95", 
  "X-RateLimit-Reset": "1639234567" // Unix timestamp
}

// 429 Too Many Requests
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}
```

## 🔧 Development & Testing

### Health Check Endpoint
```javascript
GET /
// Response
{
  "message": "VoiceApp Backend API",
  "status": "healthy"
}

GET /api/ai-host/health
// Response  
{
  "status": "healthy",
  "openai_available": true,
  "features": ["tts", "stt", "topic_extraction"],
  "timestamp": "2023-12-01T10:00:00Z"
}
```

### Environment Variables Needed
```bash
# Firebase
FIREBASE_CREDENTIALS_PATH=/path/to/credentials.json

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LiveKit
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_URL=wss://your-livekit-server.com

# Redis
REDIS_URL=redis://localhost:6379

# Application
PORT=8000
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.com
```

### Sample Integration Code
```javascript
// Complete VoiceApp integration example
class VoiceAppClient {
  constructor(apiUrl, firebaseApp) {
    this.apiUrl = apiUrl
    this.firebaseApp = firebaseApp
    this.auth = getAuth(firebaseApp)
    this.websockets = {}
  }

  async getAuthHeaders() {
    const user = this.auth.currentUser
    if (!user) throw new Error('User not authenticated')
    
    const token = await user.getIdToken()
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }

  // Authentication
  async register(email, password, displayName) {
    const userCredential = await createUserWithEmailAndPassword(this.auth, email, password)
    
    return await this.apiCall('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        firebase_uid: userCredential.user.uid,
        email: email,
        display_name: displayName
      })
    })
  }

  // AI Services
  async extractTopics(text) {
    return await this.apiCall('/api/ai-host/extract-topics', {
      method: 'POST',
      body: JSON.stringify({ text })
    })
  }

  async generateTTS(text, voice = 'nova') {
    const response = await fetch(`${this.apiUrl}/api/ai-host/tts`, {
      method: 'POST',
      headers: await this.getAuthHeaders(),
      body: JSON.stringify({ text, voice })
    })
    
    return await response.blob()
  }

  // Matching
  async requestMatch(topics, maxParticipants = 3) {
    return await this.apiCall('/api/matching/match', {
      method: 'POST',
      body: JSON.stringify({
        preferred_topics: topics,
        max_participants: maxParticipants
      })
    })
  }

  // WebSocket connections
  connectToMatching(userId) {
    const ws = new WebSocket(`${this.apiUrl.replace('http', 'ws')}/api/matching/ws?user_id=${userId}`)
    this.websockets.matching = ws
    return ws
  }

  connectToRoom(roomId, livekitName, userId) {
    const ws = new WebSocket(`${this.apiUrl.replace('http', 'ws')}/api/rooms/ws/${roomId}?livekit_name=${livekitName}&user_id=${userId}`)
    this.websockets.room = ws
    return ws
  }

  // Helper method
  async apiCall(endpoint, options = {}) {
    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      ...options,
      headers: {
        ...await this.getAuthHeaders(),
        ...options.headers
      }
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }

    return await response.json()
  }

  // Cleanup
  disconnect() {
    Object.values(this.websockets).forEach(ws => ws.close())
    this.websockets = {}
  }
}

// Usage
const voiceApp = new VoiceAppClient('https://your-api.com', firebaseApp)

// Register and connect
await voiceApp.register('user@example.com', 'password', 'John Doe')
const matchingWs = voiceApp.connectToMatching(userId)
```

---

## 📚 Quick Reference

### Key Endpoints Summary
- **Health**: `GET /` 
- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/profile`
- **AI**: `POST /api/ai-host/extract-topics`, `POST /api/ai-host/tts`, `POST /api/ai-host/upload-audio`
- **Matching**: `POST /api/matching/match`, `POST /api/matching/ai-match`, `GET /api/matching/status`
- **Rooms**: `POST /api/rooms/`, `GET /api/rooms/`, `POST /api/rooms/join`
- **Friends**: `GET /api/friends/`, `POST /api/friends/request`, `GET /api/friends/search`
- **Topics**: `GET /api/topics/`, `GET /api/topics/popular`, `POST /api/topics/preferences`
- **Recordings**: `GET /api/recordings/`, `GET /api/recordings/{id}/download`, `GET /api/recordings/{id}/transcript`

### WebSocket Endpoints Summary
- **AI Subtitle**: `wss://.../api/ai-host/live-subtitle`
- **AI Voice Chat**: `wss://.../api/ai-host/voice-chat` 
- **Room Communication**: `wss://.../api/rooms/ws/{room_id}?livekit_name=...&user_id=...`
- **Matching Queue**: `wss://.../api/matching/ws?user_id=...`
- **General Notifications**: `wss://.../api/matching/ws/general?user_id=...`

This guide covers all available endpoints and WebSocket connections in the VoiceApp backend. For the most up-to-date API documentation, refer to the OpenAPI schema at `/docs` when the server is running.