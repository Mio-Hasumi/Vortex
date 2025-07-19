

This guide provides everything frontend developers need to integrate with the VoiceApp backend.

## 🔑 **Authentication**

### **Base URL**
```javascript
const API_BASE_URL = 'https://your-app.up.railway.app'
const WS_BASE_URL = 'wss://your-app.up.railway.app'
```

### **Authentication Headers**
All protected endpoints require Firebase ID Token:
```javascript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${firebaseIdToken}`
}
```

## 📋 **API Endpoints**

### 🔐 **Authentication APIs**

#### **Register User**
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

#### **Login User**
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

#### **Get Profile**
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

### 🤖 **AI Host Services**

#### **Text-to-Speech (TTS)**
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

#### **Extract Topics from Text**
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

#### **Upload Audio for Processing**
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

#### **Start AI Session**
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

### 🎯 **Matching System**

#### **AI-Powered Matching**
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

#### **Traditional Topic-Based Matching**
```javascript
POST /api/matching/match
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "preferred_topics": ["technology", "ai"],
  "max_participants": 3,
  "language_preference": "en-US"
}
```

#### **Check Match Status**
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

#### **Cancel Match**
```javascript
POST /api/matching/cancel
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "message": "Match request cancelled"
}
```

### 🏠 **Room Management**

#### **List Rooms**
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
      "is_private": false
    }
  ],
  "total": 1
}
```

#### **Create Room**
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

#### **Get Room Details**
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
  "created_at": "2023-12-01T10:00:00Z"
}
```

### 🎙️ **Recordings**

#### **List User Recordings**
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

#### **Download Recording**
```javascript
GET /api/recordings/{recording_id}
Headers: { Authorization: "Bearer <firebase_token>" }

// Returns: Audio file stream
// Content-Type: audio/mpeg
```

#### **Get Transcript**
```javascript
GET /api/recordings/{recording_id}/transcript
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "transcript": [
    {
      "speaker_id": "uuid",
      "speaker_type": "user",
      "text": "Hello, how are you?",
      "timestamp": "2023-12-01T10:00:00Z",
      "start_time": 0.0,
      "end_time": 2.5
    }
  ],
  "total_duration": 1800
}
```

#### **Get AI Summary**
```javascript
GET /api/recordings/{recording_id}/summary
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "summary": "This conversation covered AI in entrepreneurship...",
  "key_topics": ["AI", "Entrepreneurship", "Technology"],
  "participants_count": 2,
  "duration": 1800,
  "sentiment": "positive"
}
```

### 👥 **Friends & Social**

#### **List Friends**
```javascript
GET /api/friends/
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "friends": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "friend_id": "uuid",
      "friend_name": "Jane Doe",
      "status": "accepted",
      "created_at": "2023-12-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### **Send Friend Request**
```javascript
POST /api/friends/add
Headers: { Authorization: "Bearer <firebase_token>" }
{
  "friend_id": "uuid",
  "message": "Hi! Nice meeting you in the AI discussion!"
}
```

#### **Get Friend Requests**
```javascript
GET /api/friends/requests
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "incoming_requests": [
    {
      "id": "uuid",
      "from_user_id": "uuid",
      "from_user_name": "John Doe",
      "message": "Hi! Let's be friends!",
      "created_at": "2023-12-01T10:00:00Z"
    }
  ],
  "outgoing_requests": []
}
```

#### **Search Users**
```javascript
GET /api/friends/search?q=john
Headers: { Authorization: "Bearer <firebase_token>" }

// Response
{
  "users": [
    {
      "id": "uuid",
      "display_name": "John Doe",
      "email": "john@example.com",
      "profile_image_url": "string"
    }
  ],
  "total": 1
}
```

### 🏷️ **Topics**

#### **List All Topics**
```javascript
GET /api/topics/

// Response
{
  "topics": [
    {
      "id": "uuid",
      "name": "Technology",
      "description": "Discuss latest tech trends",
      "category": "Tech",
      "difficulty_level": 2,
      "is_active": true
    }
  ],
  "total": 1
}
```

#### **Get Popular Topics**
```javascript
GET /api/topics/popular?limit=10

// Response
{
  "topics": [...],
  "total": 10
}
```

#### **Search Topics**
```javascript
GET /api/topics/search?q=AI

// Response
{
  "topics": [...],
  "total": 5
}
```

## 🔌 **WebSocket Connections**

### **Real-time AI Voice Chat**
```javascript
const ws = new WebSocket(`${WS_BASE_URL}/api/ai-host/voice-chat`)

// Connection established
ws.onopen = () => {
  console.log('Connected to AI voice chat')
}

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  switch(data.type) {
    case 'connected':
      console.log('AI greeting:', data.ai_greeting)
      break
    case 'ai_response':
      console.log('AI said:', data.text)
      break
    case 'session_started':
      console.log('Session ID:', data.session_id)
      break
  }
}

// Send voice data
const sendVoiceData = (audioBlob) => {
  ws.send(JSON.stringify({
    type: 'voice_input',
    audio_data: base64AudioData,
    session_id: sessionId
  }))
}
```

### **Live Subtitles**
```javascript
const subtitleWs = new WebSocket(`${WS_BASE_URL}/api/ai-host/live-subtitle`)

subtitleWs.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  if (data.type === 'subtitle') {
    displaySubtitle(data.text)
  }
}

// Send text for subtitle generation
const sendTextForSubtitle = (text) => {
  subtitleWs.send(JSON.stringify({
    type: 'text',
    text: text
  }))
}
```

## 💡 **Frontend Integration Examples**

### **Complete User Flow Implementation**

```javascript
class VoiceAppClient {
  constructor(firebaseAuth) {
    this.baseURL = 'https://your-app.up.railway.app'
    this.auth = firebaseAuth
  }

  async getAuthHeaders() {
    const token = await this.auth.currentUser.getIdToken()
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  // Step 1: User authentication
  async registerUser(userData) {
    const response = await fetch(`${this.baseURL}/api/auth/register`, {
      method: 'POST',
      headers: await this.getAuthHeaders(),
      body: JSON.stringify(userData)
    })
    return response.json()
  }

  // Step 2: Voice input and topic extraction
  async processVoiceInput(audioFile) {
    const formData = new FormData()
    formData.append('audio_file', audioFile)
    formData.append('extract_topics', 'true')

    const headers = await this.getAuthHeaders()
    delete headers['Content-Type'] // Let browser set for FormData

    const response = await fetch(`${this.baseURL}/api/ai-host/upload-audio`, {
      method: 'POST',
      headers,
      body: formData
    })
    return response.json()
  }

  // Step 3: AI-powered matching
  async findMatch(voiceInput) {
    const response = await fetch(`${this.baseURL}/api/matching/ai-match`, {
      method: 'POST',
      headers: await this.getAuthHeaders(),
      body: JSON.stringify({
        user_voice_input: voiceInput,
        max_participants: 2,
        language_preference: 'en-US'
      })
    })
    return response.json()
  }

  // Step 4: Generate TTS for subtitles
  async generateTTS(text, voice = 'nova') {
    const response = await fetch(`${this.baseURL}/api/ai-host/tts`, {
      method: 'POST',
      headers: await this.getAuthHeaders(),
      body: JSON.stringify({ text, voice, speed: 1.0 })
    })
    return response.blob() // Audio blob for playback
  }

  // Step 5: Get conversation recordings
  async getRecordings() {
    const response = await fetch(`${this.baseURL}/api/recordings/`, {
      headers: await this.getAuthHeaders()
    })
    return response.json()
  }
}

// Usage example
const client = new VoiceAppClient(firebase.auth())

// Complete workflow
async function startVoiceChat() {
  try {
    // 1. Record user voice
    const audioBlob = await recordUserVoice()
    
    // 2. Process voice and extract topics
    const voiceResult = await client.processVoiceInput(audioBlob)
    console.log('Topics:', voiceResult.extracted_topics)
    
    // 3. Find a match
    const matchResult = await client.findMatch(voiceResult.transcription)
    
    if (matchResult.status === 'matched') {
      // 4. Start voice chat with matched user
      startRealTimeChat(matchResult.session_id)
    } else {
      // Show waiting UI
      showWaitingForMatch(matchResult.estimated_wait_time)
    }
  } catch (error) {
    console.error('Voice chat error:', error)
  }
}
```

### **React Hook Example**
```javascript
import { useState, useEffect } from 'react'
import { useAuthState } from 'react-firebase-hooks/auth'

export function useVoiceChat() {
  const [user] = useAuthState(firebase.auth())
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [topics, setTopics] = useState([])
  const [matchStatus, setMatchStatus] = useState('idle')

  const client = new VoiceAppClient(firebase.auth())

  const startRecording = async () => {
    setIsRecording(true)
    // Implement audio recording logic
  }

  const stopRecording = async (audioBlob) => {
    setIsRecording(false)
    
    try {
      const result = await client.processVoiceInput(audioBlob)
      setTranscript(result.transcription)
      setTopics(result.extracted_topics)
      
      // Automatically start matching
      const matchResult = await client.findMatch(result.transcription)
      setMatchStatus(matchResult.status)
      
    } catch (error) {
      console.error('Processing error:', error)
    }
  }

  return {
    isRecording,
    transcript,
    topics,
    matchStatus,
    startRecording,
    stopRecording
  }
}
```

## 🚨 **Error Handling**

### **Common HTTP Status Codes**
- `200` - Success
- `401` - Unauthorized (invalid/missing Firebase token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not found
- `422` - Validation error (invalid request data)
- `500` - Server error

### **Error Response Format**
```javascript
{
  "detail": "Error message description"
}
```

### **Error Handling Example**
```javascript
async function makeAPICall(endpoint, options) {
  try {
    const response = await fetch(endpoint, options)
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(`API Error ${response.status}: ${error.detail}`)
    }
    
    return response.json()
  } catch (error) {
    console.error('API call failed:', error)
    throw error
  }
}
```

## 🔧 **Development Tips**

### **Environment Configuration**
```javascript
// config.js
export const config = {
  development: {
    API_BASE_URL: 'http://localhost:8000',
    WS_BASE_URL: 'ws://localhost:8000'
  },
  production: {
    API_BASE_URL: 'https://your-app.up.railway.app',
    WS_BASE_URL: 'wss://your-app.up.railway.app'
  }
}

export const API_BASE_URL = config[process.env.NODE_ENV].API_BASE_URL
```

### **Audio Handling**
```javascript
// Record audio for voice input
async function recordAudio(duration = 10000) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mediaRecorder = new MediaRecorder(stream)
  const chunks = []

  return new Promise((resolve) => {
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/wav' })
      resolve(blob)
    }

    mediaRecorder.start()
    setTimeout(() => mediaRecorder.stop(), duration)
  })
}
```

### **Real-time Features**
```javascript
// WebSocket connection with reconnection
class ReconnectingWebSocket {
  constructor(url) {
    this.url = url
    this.connect()
  }

  connect() {
    this.ws = new WebSocket(this.url)
    
    this.ws.onopen = () => console.log('Connected')
    this.ws.onclose = () => {
      console.log('Disconnected, reconnecting...')
      setTimeout(() => this.connect(), 1000)
    }
    this.ws.onerror = (error) => console.error('WebSocket error:', error)
  }

  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }
}
```