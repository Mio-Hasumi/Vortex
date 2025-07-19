# VoiceApp Frontend API Guide

This comprehensive guide provides everything frontend developers need to integrate with the VoiceApp backend.

## Authentication

### Base URL
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

## API Endpoints

### Authentication APIs

#### Register User
```javascript
POST /api/auth/register
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

#### Login User
```javascript
POST /api/auth/login
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

#### Get Profile
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
  "status": "online"
}
```

### AI Host Services

#### Text-to-Speech (TTS)
```javascript
// POST method
POST /api/ai-host/tts
{
  "text": "Hello, welcome to VoiceApp!",
  "voice": "nova",  // alloy, echo, fable, onyx, nova, shimmer
  "speed": 1.0      // 0.25 to 4.0
}

// Returns: MP3 audio stream
// Content-Type: audio/mpeg

// GET method (easier for simple use)
GET /api/ai-host/tts/Hello%20World?voice=nova&speed=1.0
```

#### Extract Topics from Text
```javascript
POST /api/ai-host/extract-topics
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "text": "I want to talk about AI and entrepreneurship",
  "user_context": {
    "user_id": "uuid",
    "display_name": "John"
  }
}

// Response
{
  "main_topics": ["AI", "Entrepreneurship"],
  "hashtags": ["#AI", "#Entrepreneurship", "#Tech"],
  "category": "technology",
  "sentiment": "positive",
  "conversation_style": "professional",
  "confidence": 0.95
}
```

#### Upload Audio for Processing
```javascript
POST /api/ai-host/upload-audio
Headers: { Authorization: "Bearer <firebase_token>" }
Content-Type: multipart/form-data

FormData:
- audio_file: File (wav, mp3, m4a)
- extract_topics: boolean (default: true)
- language: string (default: "en-US")

// Response
{
  "transcription": "I want to talk about AI",
  "language": "en-US",
  "duration": 3.5,
  "confidence": 0.98,
  "extracted_topics": ["AI"],
  "generated_hashtags": ["#AI", "#Technology"]
}
```

#### Start AI Session
```javascript
POST /api/ai-host/start-session
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "user_preferences": {},
  "language": "en-US",
  "voice": "nova"
}

// Response
{
  "session_id": "string",
  "ai_greeting": "Hi! Welcome to VoiceApp! What topic would you like to discuss today?",
  "session_state": "active"
}
```

### Matching System

#### AI-Powered Matching
```javascript
POST /api/matching/ai-match
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "user_voice_input": "I want to talk about AI and entrepreneurship",
  "max_participants": 2,
  "language_preference": "en-US"
}

// Response
{
  "match_id": "string",
  "session_id": "string",
  "extracted_topics": ["AI", "Entrepreneurship"],
  "generated_hashtags": ["#AI", "#Entrepreneurship"],
  "match_confidence": 0.85,
  "estimated_wait_time": 30,
  "status": "matched" // or "waiting_for_match"
}
```

#### Traditional Topic-Based Matching
```javascript
POST /api/matching/match
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "preferred_topics": ["technology", "ai"],
  "max_participants": 3,
  "language_preference": "en-US"
}
```

#### Check Match Status
```javascript
GET /api/matching/status
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "position": 2,
  "estimated_wait_time": 60,
  "queue_size": 15
}
```

#### Cancel Match
```javascript
POST /api/matching/cancel
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "message": "Match request cancelled"
}
```

#### Get Timeout Statistics
```javascript
GET /api/matching/timeout-stats?timeout_minutes=1.0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "total_queue_size": 10,
  "timeout_users_count": 3,
  "timeout_minutes": 1.0,
  "timeout_percentage": 30.0,
  "ready_for_timeout_matching": true
}
```

#### Trigger Timeout Matching (Admin)
```javascript
POST /api/matching/process-timeout-matches?timeout_minutes=1.0
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "message": "Processed timeout matching for 4 users waiting over 1.0 minute(s)",
  "timeout_users_count": 4,
  "matches_created": 2,
  "matches": [
    {
      "match_id": "uuid",
      "user1_id": "uuid",
      "user2_id": "uuid", 
      "match_type": "timeout_fallback",
      "wait_time_user1": 75.5,
      "wait_time_user2": 82.3
    }
  ]
}
```

### Timeout Matching System
VoiceApp includes an intelligent timeout matching system that prevents users from waiting indefinitely:

**How it works:**
- Users are automatically matched after waiting 1 minute (configurable)
- System randomly pairs users who have been waiting too long
- Matches are labeled as `timeout_fallback` type
- Users receive real-time WebSocket notifications

**Frontend Implementation:**
```javascript
// Monitor timeout statistics
const checkTimeoutStats = async () => {
  const response = await fetch('/api/matching/timeout-stats', {
    headers: { Authorization: `Bearer ${token}` }
  })
  const stats = await response.json()
  
  if (stats.ready_for_timeout_matching) {
    console.log(`${stats.timeout_users_count} users ready for timeout matching`)
  }
}

// Handle timeout match notifications
matchingWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  if (data.type === 'timeout_match_found') {
    showNotification(
      'Match Found!', 
      `We found you a conversation partner after ${data.wait_time} of waiting.`
    )
    redirectToChat(data.match_id, data.partner_id)
  }
}
```

### Room Management

#### List Rooms
```javascript
GET /api/rooms/
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "rooms": [
    {
      "id": "uuid",
      "name": "AI Discussion Room",
      "topic_id": "uuid",
      "current_participants": 2,
      "max_participants": 10,
      "status": "active",
      "is_private": false,
      "livekit_token": "jwt_token_here"
    }
  ],
  "total": 1
}
```

#### Create Room
```javascript
POST /api/rooms/
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "name": "My Discussion Room",
  "description": "A room for AI discussions",
  "max_participants": 5,
  "is_public": true
}
```

#### Get Room Details
```javascript
GET /api/rooms/{room_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "id": "uuid",
  "name": "AI Discussion Room",
  "description": "...",
  "current_participants": ["uuid1", "uuid2"],
  "max_participants": 10,
  "status": "active",
  "created_at": "2023-12-01T10:00:00Z",
  "livekit_token": "jwt_token_here"
}
```

### Recordings

#### List User Recordings
```javascript
GET /api/recordings/
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "recordings": [
    {
      "id": "uuid",
      "title": "AI Discussion",
      "duration": 1800,
      "file_size": 5242880,
      "status": "ready",
      "created_at": "2023-12-01T10:00:00Z",
      "participants": ["uuid1", "uuid2"]
    }
  ],
  "total": 1
}
```

#### Download Recording
```javascript
GET /api/recordings/{recording_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Returns: Audio file stream
```

#### Get Recording Transcript
```javascript
GET /api/recordings/{recording_id}/transcript
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "transcript": "Full conversation transcript...",
  "language": "en-US",
  "confidence": 0.95,
  "segments": [
    {
      "speaker": "user1",
      "text": "Hello there!",
      "start_time": 0.0,
      "end_time": 1.5
    }
  ]
}
```

#### Get AI-Generated Summary
```javascript
GET /api/recordings/{recording_id}/summary
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "summary": "The conversation covered topics about AI and technology...",
  "key_points": ["AI development", "Future trends"],
  "topics_discussed": ["AI", "Technology"],
  "sentiment": "positive",
  "duration": 1800
}
```

### Friends & Social

#### List Friends
```javascript
GET /api/friends/
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "friends": [
    {
      "user_id": "uuid",
      "display_name": "Jane Doe",
      "profile_image_url": "string",
      "status": "online",
      "friendship_since": "2023-12-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### Send Friend Request
```javascript
POST /api/friends/add
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "friend_user_id": "uuid"
}

// Response
{
  "message": "Friend request sent successfully",
  "friendship_id": "uuid"
}
```

#### Get Friend Requests
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
  "outgoing_requests": []
}
```

#### Accept/Reject Friend Request
```javascript
POST /api/friends/requests/{friendship_id}/respond
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "action": "accept" // or "reject"
}
```

#### Search Users
```javascript
GET /api/friends/search?q=john
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "users": [
    {
      "user_id": "uuid",
      "display_name": "John Doe",
      "profile_image_url": "string",
      "bio": "AI enthusiast"
    }
  ]
}
```

### Topics

#### List All Topics
```javascript
GET /api/topics/
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "Artificial Intelligence",
      "description": "Discussions about AI technology",
      "category": "Technology",
      "is_active": true
    }
  ]
}
```

#### Get Popular Topics
```javascript
GET /api/topics/popular
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "AI",
      "participant_count": 150,
      "trend_score": 0.95
    }
  ]
}
```

#### Search Topics
```javascript
GET /api/topics/search?q=technology
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "Technology",
      "description": "Tech discussions",
      "relevance_score": 0.98
    }
  ]
}
```

## WebSocket Connections

### AI Live Subtitle
```javascript
const ws = new WebSocket('wss://your-app.up.railway.app/api/ai-host/live-subtitle')

ws.onopen = () => {
  console.log('Live subtitle WebSocket connected')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Subtitle:', data)
}

// Send audio data
ws.send(JSON.stringify({
  type: 'audio_chunk',
  audio_data: base64AudioData,
  chunk_id: 'unique_id'
}))
```

### Room Communication
```javascript
const roomWs = new WebSocket(
  `wss://your-app.up.railway.app/api/rooms/ws/${roomId}?user_id=${userId}`
)

roomWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'room_joined':
      console.log('Successfully joined room', data.room_id)
      break
    case 'user_joined':
      console.log('User joined:', data.user)
      break
    case 'voice_message':
      console.log('Voice message:', data.message)
      break
    case 'ai_response':
      console.log('AI response:', data.response)
      break
  }
}

// Send messages
roomWs.send(JSON.stringify({
  type: 'text_message',
  message: 'Hello everyone!',
  user_id: userId
}))

roomWs.send(JSON.stringify({
  type: 'voice_message',
  audio_data: base64AudioData,
  user_id: userId
}))
```

### Matching Queue WebSocket
```javascript
const matchingWs = new WebSocket('wss://your-app.up.railway.app/api/matching/ws')

matchingWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'queue_position_update':
      console.log('Queue position:', data.position)
      break
    case 'match_found':
      console.log('Match found!', data.room_id)
      // Redirect to room
      break
    case 'timeout_match_found':
      console.log('Timeout match found!', data.partner_id)
      console.log('You waited:', data.wait_time)
      console.log('Match type:', data.match_type) // "timeout_fallback"
      // Show notification and redirect to conversation
      break
    case 'estimated_wait_time':
      console.log('Estimated wait:', data.seconds)
      break
    case 'queue_stats':
      console.log('Queue stats:', data.total_users_in_queue)
      break
  }
}
```

