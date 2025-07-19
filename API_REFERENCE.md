# 🚀 VoiceApp API Reference

> **Complete API documentation for the VoiceApp voice social platform**

**Base URL**: `https://voiceapp.up.railway.app` (Production) | `http://localhost:8000` (Development)  
**Authentication**: Firebase ID Token via `Authorization: Bearer <token>`  
**WebSocket**: `wss://voiceapp.up.railway.app/api/matching/ws?user_id=<uuid>`

## 🔐 **Authentication APIs**

### **POST /api/auth/signup**
Register a new user (Firebase user must be created client-side first)

**Request Body**:
```json
{
  "firebase_uid": "firebase-generated-uid",
  "display_name": "John Doe",
  "email": "john@example.com"
}
```

**Response**:
```json
{
  "user_id": "uuid-here",
  "display_name": "John Doe", 
  "email": "john@example.com",
  "message": "User registered successfully"
}
```

### **POST /api/auth/signin**
Sign in existing user

**Request Body**:
```json
{
  "firebase_uid": "firebase-generated-uid",
  "email": "john@example.com"
}
```

**Response**:
```json
{
  "user_id": "uuid-here",
  "display_name": "John Doe",
  "email": "john@example.com", 
  "message": "User authenticated successfully"
}
```

### **GET /api/auth/profile**
Get current user profile

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "id": "uuid-here",
  "display_name": "John Doe",
  "email": "john@example.com"
}
```

### **PUT /api/auth/profile**
Update user profile

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "display_name": "John Smith",
  "bio": "Updated bio"
}
```

---

## 📋 **Topics APIs**

### **GET /api/topics/**
Get all available topics

**Response**:
```json
{
  "topics": [
    {
      "id": "uuid-here",
      "name": "Technology",
      "description": "Discuss latest tech trends",
      "category": "Tech",
      "difficulty_level": 3,
      "is_active": true
    }
  ],
  "total": 8
}
```

### **GET /api/topics/{topic_id}**
Get specific topic details

**Response**:
```json
{
  "id": "uuid-here",
  "name": "Technology",
  "description": "Discuss latest tech trends", 
  "category": "Tech",
  "difficulty_level": 3,
  "is_active": true
}
```

### **POST /api/topics/preferences**
Save user topic preferences

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "preferred_topics": ["uuid-1", "uuid-2"],
  "difficulty_preference": 3
}
```

### **GET /api/topics/preferences**
Get user topic preferences

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "user_id": "uuid-here",
  "preferred_topics": ["uuid-1", "uuid-2"],
  "difficulty_preference": 3,
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

## 🎯 **Matching APIs**

### **POST /api/matching/request**
Request to be matched with other users

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "preferred_topics": ["topic-uuid-1", "topic-uuid-2"],
  "max_participants": 3,
  "language_preference": "en"
}
```

**Response**:
```json
{
  "match_id": "uuid-here",
  "room_id": "",
  "participants": ["user-uuid"],
  "topic": "Technology",
  "status": "pending",
  "estimated_wait_time": 30
}
```

### **GET /api/matching/status**
Get current matching status

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "match_id": "uuid-here",
  "status": "matched",
  "room_id": "room-uuid-here",
  "participants": ["user1-uuid", "user2-uuid"],
  "topic": "Technology"
}
```

### **DELETE /api/matching/cancel**
Cancel matching request

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Match request cancelled successfully"
}
```

### **GET /api/matching/history**
Get user's matching history

**Headers**: `Authorization: Bearer <firebase-token>`

**Query Parameters**:
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset (default: 0)

**Response**:
```json
{
  "matches": [
    {
      "match_id": "uuid-here",
      "topic": "Technology",
      "participants": ["user1", "user2"],
      "created_at": "2024-01-01T12:00:00Z",
      "status": "completed"
    }
  ],
  "total": 5
}
```

---

## 🏠 **Room APIs**

### **GET /api/rooms/**
List active rooms

**Headers**: `Authorization: Bearer <firebase-token>`

**Query Parameters**:
- `status`: Filter by room status (default: all)
- `limit`: Number of results (default: 20)

**Response**:
```json
{
  "rooms": [
    {
      "id": "room-uuid",
      "name": "Tech Discussion",
      "topic": "Technology",
      "participants": ["user1", "user2"],
      "max_participants": 5,
      "is_private": false,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 3
}
```

### **POST /api/rooms/**
Create new room

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "name": "My Tech Room",
  "topic": "Technology",
  "max_participants": 5,
  "is_private": false
}
```

**Response**:
```json
{
  "room_id": "uuid-here",
  "name": "My Tech Room",
  "topic": "Technology",
  "livekit_token": "jwt-token-here",
  "livekit_room_name": "room-uuid"
}
```

### **GET /api/rooms/{room_id}**
Get room details

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "id": "room-uuid",
  "name": "Tech Discussion",
  "topic": "Technology", 
  "participants": [
    {
      "user_id": "user1-uuid",
      "display_name": "John Doe",
      "joined_at": "2024-01-01T12:00:00Z"
    }
  ],
  "max_participants": 5,
  "is_private": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### **POST /api/rooms/{room_id}/join**
Join a room

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Joined room successfully",
  "livekit_token": "jwt-token-here",
  "room_name": "room-uuid"
}
```

### **POST /api/rooms/{room_id}/leave**
Leave a room

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Left room successfully"
}
```

### **GET /api/rooms/{room_id}/participants**
Get room participants

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "participants": [
    {
      "user_id": "user1-uuid",
      "display_name": "John Doe",
      "joined_at": "2024-01-01T12:00:00Z",
      "is_speaking": false
    }
  ],
  "total": 2
}
```

---

## 👥 **Friend APIs**

### **GET /api/friends/**
Get friends list

**Headers**: `Authorization: Bearer <firebase-token>`

**Query Parameters**:
- `status`: Filter by friendship status (default: all)
- `limit`: Number of results (default: 50)

**Response**:
```json
{
  "friends": [
    {
      "user_id": "friend-uuid",
      "display_name": "Jane Smith",
      "status": "online",
      "last_seen": "2024-01-01T12:00:00Z",
      "friendship_status": "accepted"
    }
  ],
  "total": 15
}
```

### **POST /api/friends/request**
Send friend request

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "user_id": "target-user-uuid",
  "message": "Let's be friends!"
}
```

**Response**:
```json
{
  "message": "Friend request sent successfully",
  "request_id": "request-uuid"
}
```

### **GET /api/friends/requests**
Get friend requests

**Headers**: `Authorization: Bearer <firebase-token>`

**Query Parameters**:
- `type`: "received" or "sent" (default: "received")
- `limit`: Number of results (default: 20)

**Response**:
```json
{
  "requests": [
    {
      "id": "request-uuid",
      "from_user_id": "sender-uuid",
      "from_display_name": "John Doe", 
      "to_user_id": "receiver-uuid",
      "to_display_name": "Jane Smith",
      "status": "pending",
      "created_at": "2024-01-01T12:00:00Z",
      "message": "Let's be friends!"
    }
  ],
  "total": 3
}
```

### **POST /api/friends/accept/{request_id}**
Accept friend request

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Friend request accepted successfully"
}
```

### **POST /api/friends/reject/{request_id}**
Reject friend request

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Friend request rejected successfully"
}
```

### **DELETE /api/friends/{friend_id}**
Remove friend

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Friend removed successfully"
}
```

### **POST /api/friends/block/{user_id}**
Block user

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "User blocked successfully"
}
```

### **DELETE /api/friends/block/{user_id}**
Unblock user

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "User unblocked successfully"
}
```

---

## 🎵 **Recording APIs**

### **GET /api/recordings/**
List user recordings

**Headers**: `Authorization: Bearer <firebase-token>`

**Query Parameters**:
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset (default: 0)

**Response**:
```json
{
  "recordings": [
    {
      "id": "recording-uuid",
      "room_id": "room-uuid",
      "title": "Tech Discussion",
      "duration_seconds": 1800,
      "file_size_bytes": 5242880,
      "created_at": "2024-01-01T12:00:00Z",
      "participants": ["user1", "user2"]
    }
  ],
  "total": 10
}
```

### **GET /api/recordings/{recording_id}**
Get recording details

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "id": "recording-uuid",
  "room_id": "room-uuid", 
  "title": "Tech Discussion",
  "description": "Great conversation about AI",
  "duration_seconds": 1800,
  "file_size_bytes": 5242880,
  "created_at": "2024-01-01T12:00:00Z",
  "participants": [
    {
      "user_id": "user1-uuid",
      "display_name": "John Doe"
    }
  ],
  "tags": ["technology", "ai"],
  "is_public": false
}
```

### **PUT /api/recordings/{recording_id}**
Update recording metadata

**Headers**: `Authorization: Bearer <firebase-token>`

**Request Body**:
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "tags": ["tech", "discussion"],
  "is_public": true
}
```

**Response**:
```json
{
  "message": "Recording metadata updated successfully"
}
```

### **DELETE /api/recordings/{recording_id}**
Delete recording

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "message": "Recording deleted successfully"
}
```

### **GET /api/recordings/{recording_id}/download**
Get download URL for recording

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "download_url": "https://firebase-storage-url.com/recording.wav",
  "expires_at": "2024-01-01T13:00:00Z"
}
```

### **POST /api/recordings/{recording_id}/share**
Generate shareable link (TODO: Implementation needed)

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "share_url": "https://voiceapp.com/shared/recordings/uuid?token=abc123",
  "expires_at": "2023-12-02T10:00:00Z"
}
```

### **GET /api/recordings/{recording_id}/transcript**
Get recording transcript (TODO: AI integration needed)

**Headers**: `Authorization: Bearer <firebase-token>`

**Response**:
```json
{
  "transcript": [
    {
      "speaker": "user-1",
      "text": "Hello everyone, welcome to our discussion!",
      "timestamp": 0,
      "confidence": 0.95
    }
  ],
  "language": "en",
  "duration": 1800
}
```

---

## ⚡ **WebSocket APIs**

### **WebSocket: /api/matching/ws?user_id=<uuid>**
Real-time matching updates

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/matching/ws?user_id=user-uuid-here');
```

**Messages Received**:

**Welcome Message**:
```json
{
  "type": "welcome",
  "connection_id": "conn-id",
  "user_id": "user-uuid",
  "message": "Successfully connected to matching WebSocket",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Queue Update**:
```json
{
  "type": "queue_update", 
  "position": 3,
  "estimated_wait_time": 90,
  "queue_size": 8,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Match Found**:
```json
{
  "type": "match_found",
  "room_id": "room-uuid",
  "topic": "Technology",
  "participants": ["user1", "user2"],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**User Status Change**:
```json
{
  "type": "user_status_change",
  "user_id": "user-uuid",
  "is_online": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Friend Request Received**:
```json
{
  "type": "friend_request_received",
  "from_user_id": "sender-uuid",
  "request_id": "request-uuid",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Messages to Send**:

**Ping**:
```json
{
  "type": "ping"
}
```

### **WebSocket: /api/matching/ws/general?user_id=<uuid>**
General notifications and updates

Same connection pattern and message types as matching WebSocket.

---

## 📊 **Response Codes**

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

## 🔧 **Error Response Format**

```json
{
  "detail": "Error message describing what went wrong"
}
```

## 🎯 **Rate Limiting**

- **Authentication endpoints**: 5 requests per minute
- **General API**: 100 requests per minute
- **WebSocket connections**: 10 connections per user
- **File uploads**: 50MB total per hour

---

## 📝 **Notes**

### **Authentication**
- All endpoints except `/api/auth/signup` and `/api/auth/signin` require Firebase authentication
- Use Firebase Client SDK to obtain ID tokens
- Include token in Authorization header: `Bearer <firebase-id-token>`

### **WebSocket Authentication**
- User ID must be provided as query parameter
- No Bearer token required for WebSocket connections
- Connection automatically registers user as online

### **File Uploads**
- Recording files are automatically uploaded during room sessions
- Manual uploads not currently supported via API
- All files stored in Firebase Storage with automatic CDN

### **Pagination**
- Most list endpoints support `limit` and `offset` parameters
- Default limit is typically 20-50 items
- Maximum limit is usually 100 items

---

**Last Updated**: January 2024  
**API Version**: 1.0  
**Documentation**: Always refer to `/docs` endpoint for interactive documentation 