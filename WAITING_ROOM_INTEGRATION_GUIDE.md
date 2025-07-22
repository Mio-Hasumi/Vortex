# WaitingRoomAgent Integration Guide

## Overview

The `WaitingRoomAgent` is a new AI-powered conversation companion built using the OpenAI Realtime API and LiveKit Agents framework. It provides intelligent voice interactions for users waiting for matches, following the same architectural patterns as the `VortexAgent` but optimized for waiting room scenarios.

## Key Features

- **Real-time Voice Conversation**: Uses OpenAI Realtime API for natural voice interactions
- **Topic Extraction**: Automatically extracts conversation topics for better matching  
- **Hashtag Generation**: Creates relevant hashtags for user matching algorithms
- **Session Management**: Handles conversation flow and state transitions
- **LiveKit Integration**: Seamless integration with LiveKit rooms and participants

## Architecture

### Components

1. **WaitingRoomAgent**: Main agent class handling conversation logic
2. **AIHostService**: Enhanced service for managing agent sessions
3. **WaitingRoomEntrypoint**: Deployment entrypoint for LiveKit agents worker
4. **OpenAIService**: Backend service providing GPT-4o Realtime API access

### Key Differences from Legacy System

| Legacy AI Host | New WaitingRoomAgent |
|----------------|---------------------|
| STT → LLM → TTS pipeline | Integrated OpenAI Realtime API |
| Manual prompt engineering | Agent-based conversation management |
| Text-based processing | Native audio processing |
| Basic state management | Comprehensive session lifecycle |

## Integration Steps

### 1. Environment Setup

Ensure you have the required environment variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional

# LiveKit Configuration  
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
LIVEKIT_URL=wss://your-livekit-server.com
```

### 2. Install Dependencies

The WaitingRoomAgent requires the following packages:

```bash
pip install livekit-agents[openai]
pip install livekit-plugins-openai
pip install livekit-plugins-silero  # For VAD
```

### 3. Basic Usage

#### Creating a Waiting Room Session

```python
from infrastructure.ai import OpenAIService, AIHostService, create_waiting_room_agent_session
from livekit import rtc

# Initialize services
openai_service = OpenAIService(api_key="your-openai-key")
ai_host_service = AIHostService(openai_service=openai_service)

# Create user context
user_context = {
    "user_id": "user_12345",
    "user_name": "Alice",
    "session_state": "greeting",
    "extracted_topics": [],
    "generated_hashtags": [],
    "matching_preferences": {"interests": ["technology", "AI"]}
}

# Create agent session
session, agent = create_waiting_room_agent_session(
    openai_service=openai_service,
    ai_host_service=ai_host_service,
    user_context=user_context
)
```

#### Starting the Agent in a Room

```python
# Connect to LiveKit room
room = rtc.Room()
await room.connect(url="wss://your-livekit-server.com", token="your-token")

# Start the agent session
await session.start(room=room, agent=agent)

# The agent will now handle voice interactions automatically
print("WaitingRoomAgent is ready for conversation!")
```

### 4. Deploying as LiveKit Agent Worker

#### Option A: Direct Deployment

```python
# infrastructure/ai/waiting_room_entrypoint.py
from livekit.agents import cli, WorkerOptions
from infrastructure.ai.waiting_room_entrypoint import entrypoint, prewarm

if __name__ == "__main__":
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        agent_name="waiting-room-agent",
    )
    cli.run_app(worker_options)
```

Run the worker:
```bash
python infrastructure/ai/waiting_room_entrypoint.py start
```

#### Option B: Integration with Existing API

```python
# In your API endpoint
from infrastructure.ai import AIHostService

@app.post("/start-waiting-room")
async def start_waiting_room(request: WaitingRoomRequest):
    ai_host_service = get_ai_host_service()
    
    # Create waiting room session with agent
    session = await ai_host_service.start_waiting_room_session(
        user_id=request.user_id,
        user_context={
            "user_name": request.user_name,
            "preferences": request.preferences
        },
        livekit_room=None  # Will connect later
    )
    
    return {
        "session_id": session.session_id,
        "status": "created",
        "agent_ready": session.agent_session is not None
    }
```

## API Integration Examples

### 1. Enhanced AI Host Endpoints

```python
# api/routers/ai_host.py
from infrastructure.ai import AIHostService

@router.post("/start-enhanced-session")
async def start_enhanced_session(
    request: StartSessionRequest,
    ai_host_service=Depends(get_ai_host_service),
    current_user: User = Depends(get_current_user)
):
    """Start a new waiting room session with WaitingRoomAgent"""
    
    user_context = {
        "user_id": str(current_user.id),
        "user_name": current_user.display_name,
        "session_state": "greeting",
        "preferences": request.preferences,
        "language": request.language or "en-US"
    }
    
    session = await ai_host_service.start_waiting_room_session(
        user_id=current_user.id,
        user_context=user_context
    )
    
    return {
        "session_id": session.session_id,
        "agent_available": session.agent_session is not None,
        "status": "ready"
    }

@router.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    ai_host_service=Depends(get_ai_host_service)
):
    """Get current session summary including extracted topics"""
    
    summary = await ai_host_service.get_agent_session_summary(session_id)
    if not summary:
        raise HTTPException(404, "Session not found")
    
    return summary
```

### 2. LiveKit Room Integration

```python
# When creating a waiting room
@router.post("/rooms/waiting-room")
async def create_waiting_room(
    request: CreateWaitingRoomRequest,
    current_user: User = Depends(get_current_user)
):
    # Create LiveKit room
    room_name = f"waiting_{current_user.id}_{int(time.time())}"
    
    # Start waiting room agent
    ai_host_service = get_ai_host_service()
    session = await ai_host_service.start_waiting_room_session(
        user_id=current_user.id,
        user_context={
            "user_name": current_user.display_name,
            "room_name": room_name
        }
    )
    
    # Generate token for user
    token = generate_livekit_token(
        room_name=room_name,
        participant_identity=str(current_user.id),
        participant_name=current_user.display_name
    )
    
    return {
        "room_name": room_name,
        "token": token,
        "session_id": session.session_id,
        "agent_active": True
    }
```

## Configuration Options

### Agent Behavior

```python
# Customize agent behavior through user context
user_context = {
    "session_state": "greeting",  # greeting, topic_extraction, matching
    "conversation_style": "casual",  # casual, professional, friendly
    "language": "en-US",  # Language preference
    "topics_required": 3,  # Minimum topics to extract
    "matching_timeout": 300,  # Seconds before timeout
    "voice_preference": "nova"  # OpenAI voice preference
}
```

### OpenAI Realtime API Settings

```python
# In create_waiting_room_agent_session
rt_llm = realtime.RealtimeModel(
    model="gpt-4o-realtime-preview-2024-12-17",
    voice="nova",  # alloy, echo, fable, onyx, nova, shimmer
    temperature=0.7,  # Creativity level
    modalities=["text", "audio"],
    turn_detection=TurnDetection(
        type="server_vad",
        threshold=0.5,
        silence_duration_ms=800,  # Longer for waiting room
    ),
)
```

## Monitoring and Analytics

### Session Monitoring

```python
# Get real-time session status
agent_summary = waiting_room_agent.get_session_summary()
print(f"Topics extracted: {agent_summary['topics_extracted']}")
print(f"Session duration: {agent_summary['session_duration_seconds']}s")
print(f"Matching ready: {agent_summary.get('matching_ready', False)}")
```

### Event Handling

```python
# Monitor agent events
@session.on("conversation_item_added") 
def on_conversation_item(item):
    print(f"New conversation item: {item}")

@session.on("speech_created")
def on_speech_created(speech_handle):
    print("Agent started speaking")
```

## Best Practices

### 1. Error Handling

```python
try:
    session = await ai_host_service.start_waiting_room_session(
        user_id=user_id,
        user_context=user_context
    )
except Exception as e:
    logger.error(f"Failed to start waiting room session: {e}")
    # Fallback to legacy system
    fallback_session = await ai_host_service.start_legacy_session(user_id)
```

### 2. Resource Management

```python
# Always cleanup agent sessions
async def cleanup_waiting_room(session_id: str):
    session = await ai_host_service.get_session(session_id)
    if session and session.agent_session:
        await session.cleanup_agent_session()
```

### 3. Performance Optimization

```python
# Use prewarming for production
def prewarm(proc: agents.JobProcess):
    openai_service = get_openai_service()
    proc.userdata["openai_service"] = openai_service
    
    # Pre-load VAD model
    from livekit.agents.vad.webrtc import WebRTCVAD
    proc.userdata["vad"] = WebRTCVAD()
```

## Migration from Legacy System

### 1. Gradual Migration

```python
# Feature flag for new system
USE_WAITING_ROOM_AGENT = os.getenv("USE_WAITING_ROOM_AGENT", "false").lower() == "true"

if USE_WAITING_ROOM_AGENT and openai_service_available():
    session = await ai_host_service.start_waiting_room_session(user_id, context)
else:
    session = await ai_host_service.start_session(user_id, context)  # Legacy
```

### 2. Data Migration

```python
# Convert legacy sessions to new format
def migrate_legacy_session(legacy_session):
    return {
        "session_id": legacy_session.session_id,
        "user_id": legacy_session.user_id,
        "extracted_topics": legacy_session.extracted_topics,
        "generated_hashtags": legacy_session.generated_hashtags,
        "session_state": map_legacy_state(legacy_session.state)
    }
```

## Troubleshooting

### Common Issues

1. **OpenAI API Key Issues**
   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   python -c "from infrastructure.ai import get_openai_service; print(get_openai_service())"
   ```

2. **LiveKit Connection Issues**
   ```python
   # Test LiveKit connection
   import livekit
   room = livekit.Room()
   await room.connect("wss://your-server.com", "your-token")
   ```

3. **Agent Not Responding**
   ```python
   # Check agent session status  
   if not session.agent_session:
       logger.error("Agent session not initialized")
   
   # Check OpenAI service
   if not openai_service:
       logger.error("OpenAI service not available")
   ```

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger("waiting_room_agent").setLevel(logging.DEBUG)
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
```

## Examples and Use Cases

See the `/examples` directory for:
- Basic waiting room setup
- Custom conversation flows  
- Integration with matching systems
- Multi-language support
- Custom voice personalities

## Support

For issues and questions:
1. Check the LiveKit Agents documentation
2. Review OpenAI Realtime API documentation  
3. File issues in the project repository
4. Contact the VoiceApp development team 