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

## Error Handling

### Standard Error Response
```javascript
{
  "detail": "Error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2023-12-01T10:00:00Z"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Handling Example
```javascript
const apiCall = async () => {
  try {
    const response = await fetch('/api/auth/profile', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'API request failed')
    }
    
    const data = await response.json()
    return data
  } catch (error) {
    console.error('API Error:', error.message)
    throw error
  }
}
```

## Frontend Integration Examples

### React Integration
```jsx
import { useState, useEffect } from 'react'

const VoiceAppAPI = {
  baseURL: 'https://your-app.up.railway.app',
  
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const token = localStorage.getItem('firebaseToken')
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
      },
      ...options
    }
    
    const response = await fetch(url, config)
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }
    
    return response.json()
  },
  
  // Auth methods
  async getProfile() {
    return this.request('/api/auth/profile')
  },
  
  // AI methods
  async extractTopics(text) {
    return this.request('/api/ai-host/extract-topics', {
      method: 'POST',
      body: JSON.stringify({ text })
    })
  },
  
  // TTS method
  async textToSpeech(text, voice = 'nova') {
    const response = await fetch(
      `${this.baseURL}/api/ai-host/tts/${encodeURIComponent(text)}?voice=${voice}`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('firebaseToken')}`
        }
      }
    )
    return response.blob() // Returns audio blob
  }
}

// Usage in React component
const MyComponent = () => {
  const [profile, setProfile] = useState(null)
  const [topics, setTopics] = useState([])
  
  useEffect(() => {
    VoiceAppAPI.getProfile()
      .then(setProfile)
      .catch(console.error)
  }, [])
  
  const handleTopicExtraction = async (text) => {
    try {
      const result = await VoiceAppAPI.extractTopics(text)
      setTopics(result.main_topics)
    } catch (error) {
      console.error('Topic extraction failed:', error)
    }
  }
  
  return (
    <div>
      {profile && <h1>Welcome, {profile.display_name}!</h1>}
      {/* Your UI here */}
    </div>
  )
}
```

### Audio Recording Integration
```javascript
class AudioRecorder {
  constructor() {
    this.mediaRecorder = null
    this.audioChunks = []
  }
  
  async startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.mediaRecorder = new MediaRecorder(stream)
    
    this.mediaRecorder.ondataavailable = (event) => {
      this.audioChunks.push(event.data)
    }
    
    this.mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' })
      await this.uploadAudio(audioBlob)
      this.audioChunks = []
    }
    
    this.mediaRecorder.start()
  }
  
  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop()
    }
  }
  
  async uploadAudio(audioBlob) {
    const formData = new FormData()
    formData.append('audio_file', audioBlob, 'recording.wav')
    formData.append('extract_topics', 'true')
    
    const token = localStorage.getItem('firebaseToken')
    
    try {
      const response = await fetch('/api/ai-host/upload-audio', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
      
      const result = await response.json()
      console.log('Upload result:', result)
      return result
    } catch (error) {
      console.error('Audio upload failed:', error)
    }
  }
}
```

## Performance Optimization

### Caching Strategies
```javascript
// Cache user profile
const cachedProfile = localStorage.getItem('userProfile')
if (cachedProfile && Date.now() - JSON.parse(cachedProfile).timestamp < 300000) {
  // Use cached data if less than 5 minutes old
  setProfile(JSON.parse(cachedProfile).data)
} else {
  // Fetch fresh data
  VoiceAppAPI.getProfile().then(profile => {
    localStorage.setItem('userProfile', JSON.stringify({
      data: profile,
      timestamp: Date.now()
    }))
    setProfile(profile)
  })
}
```

### WebSocket Connection Management
```javascript
class WebSocketManager {
  constructor(url) {
    this.url = url
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 1000
  }
  
  connect() {
    this.ws = new WebSocket(this.url)
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.attemptReconnect()
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++
        console.log(`Reconnect attempt ${this.reconnectAttempts}`)
        this.connect()
      }, this.reconnectInterval * this.reconnectAttempts)
    }
  }
  
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }
}
```

## Production Considerations

### Security Best Practices
1. Always validate Firebase tokens on the backend
2. Use HTTPS in production
3. Implement rate limiting
4. Sanitize user inputs
5. Use secure WebSocket connections (WSS)

### Performance Tips
1. Cache API responses when appropriate
2. Use WebSocket connections efficiently
3. Implement proper error handling and retry logic
4. Optimize audio file sizes for uploads
5. Use pagination for large data sets

### Monitoring and Debugging
1. Implement proper logging
2. Monitor WebSocket connection status
3. Track API response times
4. Monitor error rates
5. Use proper error boundaries in React

This guide provides comprehensive coverage of the VoiceApp backend API. For additional support or questions, please refer to the main repository documentation.