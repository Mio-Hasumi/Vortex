"""
AI Host API routes for VoiceApp

Provides endpoints for AI-driven conversation hosting:
- Text-to-Speech (TTS) for AI voice
- Real-time subtitles via WebSocket
- Topic extraction and hashtag generation
- AI conversation management
"""

import asyncio
from datetime import datetime

from infrastructure.container import container
from infrastructure.ai.openai_service import OpenAIService
from infrastructure.ai.ai_host_service import AIHostService
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.room_repository import RoomRepository
from infrastructure.repositories.matching_repository import MatchingRepository
from infrastructure.repositories.recording_repository import RecordingRepository
from infrastructure.repositories.topic_repository import TopicRepository
from infrastructure.repositories.friend_repository import FriendRepository
from infrastructure.middleware.firebase_auth_middleware import FirebaseAuthMiddleware, get_current_user
from infrastructure.livekit.livekit_service import LiveKitService
from infrastructure.redis.redis_service import RedisService
from infrastructure.websocket.connection_manager import ConnectionManager
from infrastructure.websocket.event_broadcaster import EventBroadcaster

from domain.entities import User, Room, Match, Topic, Friendship, Recording

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import json
import io
import logging
import base64
import asyncio
from datetime import datetime

# 🔴 AI PROCESSING CONTROL FLAG
AI_PROCESSING_ENABLED = False  # Set to False to block all OpenAI processing

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class StartSessionRequest(BaseModel):
    user_preferences: Optional[Dict[str, Any]] = None
    language: Optional[str] = "en-US"
    voice: Optional[str] = "nova"


class StartSessionResponse(BaseModel):
    session_id: str
    ai_greeting: str
    audio_url: Optional[str] = None
    session_state: str


class ProcessInputRequest(BaseModel):
    session_id: str
    user_input: str


class ProcessInputResponse(BaseModel):
    session_id: str
    ai_response: str
    audio_url: Optional[str] = None
    session_state: str
    extracted_topics: List[str] = []
    generated_hashtags: List[str] = []
    next_action: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "nova"
    speed: Optional[float] = 1.0


class TopicExtractionRequest(BaseModel):
    text: str
    user_context: Optional[Dict[str, Any]] = None


class TopicExtractionResponse(BaseModel):
    main_topics: List[str]
    hashtags: List[str]
    category: str
    sentiment: str
    conversation_style: str
    confidence: float


class VoiceTopicExtractionResponse(BaseModel):
    transcription: str
    main_topics: List[str]
    hashtags: List[str]
    category: str
    sentiment: str
    conversation_style: str
    confidence: float


# Dependency injection
def get_ai_host_service():
    return container.get_ai_host_service()


def get_openai_service():
    return container.get_openai_service()


# AI Host Session Management
@router.post("/start-session", response_model=StartSessionResponse)
async def start_ai_session(
    request: StartSessionRequest,
    ai_host_service=Depends(get_ai_host_service),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new AI host session for the user
    """
    try:
        logger.info(f"🎭 Starting AI host session for user: {current_user.id}")

        # Prepare user context
        user_context = {
            "user_id": str(current_user.id),
            "display_name": current_user.display_name,
            "email": current_user.email,
            "preferences": request.user_preferences or {},
        }

        # Start AI host session
        session = await ai_host_service.start_session(
            user_id=current_user.id, user_context=user_context
        )

        # Use simple static greeting
        ai_greeting = "Hi! I'm Vortex. What would you like to talk about?"

        return StartSessionResponse(
            session_id=session.session_id,
            ai_greeting=ai_greeting,
            session_state=session.state,
        )

    except Exception as e:
        logger.error(f"❌ Failed to start AI session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start AI session: {str(e)}",
        )


@router.post("/process-input", response_model=ProcessInputResponse)
async def process_user_input(
    request: ProcessInputRequest,
    ai_host_service=Depends(get_ai_host_service),
    current_user: User = Depends(get_current_user),
):
    """
    Process user input and get AI host response
    """
    # 🔴 BLOCK AI PROCESSING IF DISABLED
    if not AI_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing is currently disabled"
        )
    
    try:
        logger.info(f"🎙️ Processing user input for session: {request.session_id}")

        # Process user input through AI host
        response_data = await ai_host_service.process_user_input(
            session_id=request.session_id, user_input=request.user_input
        )

        return ProcessInputResponse(
            session_id=request.session_id,
            ai_response=response_data.get("response_text", ""),
            session_state=response_data.get("session_state", "unknown"),
            extracted_topics=response_data.get("extracted_topics", []),
            generated_hashtags=response_data.get("generated_hashtags", []),
            next_action=response_data.get("next_action"),
        )

    except Exception as e:
        logger.error(f"❌ Failed to process user input: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process input: {str(e)}",
        )


# Text-to-Speech Endpoints (Urgently needed by frontend!)
@router.post("/tts")
async def text_to_speech(
    request: TTSRequest, openai_service=Depends(get_openai_service)
):
    """
    Convert text to speech using OpenAI TTS
    This endpoint can be called directly by the frontend to obtain AI voice
    """
    # 🔴 BLOCK AI PROCESSING IF DISABLED
    if not AI_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing is currently disabled"
        )
    
    try:
        logger.info(f"🔊 TTS request for text: '{request.text[:50]}...'")

        # Debug: Check if text_to_speech is a coroutine function
        import inspect

        logger.info(
            f"🔍 is coroutine? {inspect.iscoroutinefunction(openai_service.text_to_speech)}"
        )

        # Generate TTS audio
        audio_bytes = await openai_service.text_to_speech(
            text=request.text, voice=request.voice, speed=request.speed
        )

        # Return audio as streaming response
        # Use asynchronous generator function to stream audio data
        async def audio_streamer():
            # Return audio data in one go
            yield audio_bytes

        return StreamingResponse(
            audio_streamer(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=tts_audio.mp3",
                "Content-Length": str(len(audio_bytes)),
            },
        )

    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TTS generation failed: {str(e)}",
        )


@router.get("/test-simple")
async def test_simple_get():
    """Test GET endpoint"""
    return {"message": "GET endpoint works", "timestamp": "test"}


@router.head("/tts/{text}")
async def text_to_speech_head(text: str, voice: str = "nova", speed: float = 1.0):
    """
    HEAD endpoint for TTS resource validation (for browser preflight checks)
    """
    return Response(
        status_code=200,
        headers={
            "Content-Type": "audio/mpeg",
            "Content-Disposition": f"inline; filename=tts_{text[:10]}.mp3",
        },
    )


@router.get("/tts/{text}")
async def text_to_speech_get(
    text: str,
    voice: str = "nova",
    speed: float = 1.0,
    openai_service=Depends(get_openai_service),
):
    """
    GET endpoint for TTS (convenient for frontend)
    Usage: /api/ai-host/tts/HelloWorld?voice=nova&speed=1.0
    """
    try:
        # Generate TTS audio
        audio_bytes = await openai_service.text_to_speech(
            text=text, voice=voice, speed=speed
        )

        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"inline; filename=tts_{text[:10]}.mp3"},
        )

    except Exception as e:
        logger.error(f"❌ TTS GET failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}",
        )


# Topic Extraction (Urgently needed by frontend!)
@router.post("/extract-topics", response_model=TopicExtractionResponse)
async def extract_topics(
    request: TopicExtractionRequest, current_user: User = Depends(get_current_user)
):
    """
    Extract topics and generate hashtags from text input
    """
    # 🔴 BLOCK AI PROCESSING IF DISABLED
    if not AI_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing is currently disabled"
        )
    
    try:
        logger.info(f"🔍 Extracting topics from text: '{request.text[:50]}...'")

        # Get OpenAI service
        openai_service = container.get_openai_service()

        # Extract topics and hashtags
        result = await openai_service.extract_topics_and_hashtags(
            text_input=request.text, user_context=request.user_context
        )

        return TopicExtractionResponse(
            main_topics=result.get("main_topics", []),
            hashtags=result.get("hashtags", []),
            category=result.get("category", "general"),
            sentiment=result.get("sentiment", "neutral"),
            conversation_style=result.get("conversation_style", "casual"),
            confidence=result.get("confidence", 0.0),
        )

    except Exception as e:
        logger.error(f"❌ Topic extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topic extraction failed: {str(e)}",
        )


@router.post("/extract-topics-from-voice", response_model=VoiceTopicExtractionResponse)
async def extract_topics_from_voice(
    audio_file: UploadFile = File(...),
    language: str = Form("en-US"),
    current_user: User = Depends(get_current_user),
):
    """
    Extract topics and hashtags from voice input using GPT-4o Audio
    """
    # 🔴 BLOCK AI PROCESSING IF DISABLED
    if not AI_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing is currently disabled"
        )
    
    try:
        logger.info(f"🎙️ Processing voice input for topic extraction")

        # Get OpenAI service
        openai_service = container.get_openai_service()

        # Read audio file
        audio_content = await audio_file.read()
        logger.info(f"📁 Audio file size: {len(audio_content)} bytes")

        # Process with GPT-4o Audio
        result = await openai_service.process_voice_input(
            audio_data=audio_content,
            language=language,
            extract_topics=True,
            generate_hashtags=True,
        )

        return VoiceTopicExtractionResponse(
            transcription=result.get("transcription", ""),
            main_topics=result.get("main_topics", []),
            hashtags=result.get("hashtags", []),
            category=result.get("category", "general"),
            sentiment=result.get("sentiment", "neutral"),
            conversation_style=result.get("conversation_style", "casual"),
            confidence=result.get("confidence", 0.0),
        )

    except Exception as e:
        logger.error(f"❌ Voice topic extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice topic extraction failed: {str(e)}",
        )


# NEW: Speech-to-Text Upload Endpoint (Core Feature!)
class STTResponse(BaseModel):
    transcription: str
    language: str
    duration: float
    confidence: float
    words: List[Dict[str, Any]] = []
    extracted_topics: Optional[List[str]] = None
    generated_hashtags: Optional[List[str]] = None


@router.post("/upload-audio", response_model=STTResponse)
async def upload_audio_for_stt(
    audio_file: UploadFile = File(...),
    extract_topics: bool = True,
    language: Optional[str] = None,
    openai_service=Depends(get_openai_service),
    current_user: User = Depends(get_current_user),
):
    """
    Upload audio file for speech-to-text conversion and optional topic extraction
    """
    # 🔴 BLOCK AI PROCESSING IF DISABLED
    if not AI_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing is currently disabled"
        )
    
    try:
        logger.info(f"🎙️ Processing audio upload for STT")

        # Read audio file
        audio_content = await audio_file.read()
        logger.info(f"📁 Audio file size: {len(audio_content)} bytes")

        # Process with OpenAI
        result = await openai_service.process_audio_upload(
            audio_data=audio_content,
            language=language or "en-US",
            extract_topics=extract_topics,
        )

        return STTResponse(
            transcription=result.get("transcription", ""),
            language=result.get("language", language or "en-US"),
            duration=result.get("duration", 0.0),
            confidence=result.get("confidence", 0.0),
            words=result.get("words", []),
            extracted_topics=result.get("extracted_topics") if extract_topics else None,
            generated_hashtags=result.get("generated_hashtags") if extract_topics else None,
        )

    except Exception as e:
        logger.error(f"❌ Audio upload processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio processing failed: {str(e)}",
        )


# Real-time Subtitle WebSocket (Urgently needed by frontend!)
@router.websocket("/live-subtitle")
async def websocket_live_subtitle(websocket: WebSocket):
    """
    WebSocket endpoint for real-time subtitle generation
    Frontend connects to this WebSocket to get real-time subtitles
    """
    try:
        # Accept WebSocket connection
        await websocket.accept()
        logger.info("🎬 Live subtitle WebSocket connected")

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Live subtitle service ready",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

        # Listen for messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                data = json.loads(message)

                if data.get("type") == "text":
                    # Generate subtitle for text
                    subtitle_data = {
                        "type": "subtitle",
                        "text": data.get("text", ""),
                        "timestamp": datetime.utcnow().isoformat(),
                        "duration": len(data.get("text", "")) * 0.1,  # Rough estimate
                    }

                    await websocket.send_text(json.dumps(subtitle_data))

                elif data.get("type") == "audio":
                    # Process audio for real-time STT and subtitle generation
                    try:
                        audio_data = data.get("audio_data")  # base64 encoded audio
                        if audio_data:
                                    # Decode base64 audio data

                            audio_bytes = base64.b64decode(audio_data)

                            # Create audio buffer for STT
                            audio_buffer = io.BytesIO(audio_bytes)
                            audio_buffer.name = "realtime_audio.wav"

                            # Get OpenAI service instance
                            openai_service = container.get_openai_service()

                            # Perform STT
                            stt_result = await openai_service.speech_to_text(
                                audio_file=audio_buffer,
                                language=data.get("language", "en-US"),
                            )

                            # Send subtitle with transcription
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "subtitle",
                                        "text": stt_result["text"],
                                        "language": stt_result.get(
                                            "language", "unknown"
                                        ),
                                        "confidence": stt_result.get("confidence", 0.0),
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                )
                            )

                        else:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": "No audio data provided",
                                    }
                                )
                            )

                    except Exception as e:
                        logger.error(f"❌ Real-time STT failed: {e}")
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "subtitle",
                                    "text": "[Speech recognition failed]",
                                    "error": str(e),
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                        )

                elif data.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        )
                    )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        logger.info("🎬 Live subtitle WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ Live subtitle WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass


# Voice Chat WebSocket (Complete AI Host Interaction)
@router.websocket("/voice-chat")
async def websocket_voice_chat(websocket: WebSocket):
    """
    AI Host Voice Chat WebSocket
    Supports real-time voice communication with GPT-4o Realtime Preview
    """
    await websocket.accept()
    logger.info("🎙️ AI Host voice chat WebSocket connected")

    session_id = None
    authenticated_user = None

    try:
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)

                # Handle authentication first
                if data.get("type") == "auth":
                    try:
                        token = data.get("token")
                        if not token:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": "Authentication token required",
                                    }
                                )
                            )
                            continue

                        # Verify Firebase token
                        from infrastructure.middleware.firebase_auth_middleware import (
                            FirebaseAuthMiddleware,
                        )
                        from infrastructure.container import container

                        auth_middleware = FirebaseAuthMiddleware(
                            container.get_user_repository()
                        )
                        decoded_token = auth_middleware.verify_firebase_token(token)
                        firebase_uid = decoded_token["uid"]

                        # Find user
                        user_repo = container.get_user_repository()
                        authenticated_user = user_repo.find_by_firebase_uid(
                            firebase_uid
                        )

                        if not authenticated_user:
                            await websocket.send_text(
                                json.dumps(
                                    {"type": "error", "message": "User not found"}
                                )
                            )
                            continue

                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "authenticated",
                                    "user_id": str(authenticated_user.id),
                                    "display_name": authenticated_user.display_name,
                                }
                            )
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ WebSocket authentication failed: {e}")
                        await websocket.send_text(
                            json.dumps(
                                {"type": "error", "message": "Authentication failed"}
                            )
                        )
                        continue

                # Require authentication for all other operations
                if not authenticated_user:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Please authenticate first by sending auth message with token",
                            }
                        )
                    )
                    continue

                if data.get("type") == "start_session":
                    # Start AI host session
                    ai_host_service = container.get_ai_host_service()

                    if ai_host_service:
                        try:
                            session = await ai_host_service.start_session(
                                user_id=authenticated_user.id,
                                user_context={
                                    "user_id": str(authenticated_user.id),
                                    "display_name": authenticated_user.display_name,
                                    "email": authenticated_user.email,
                                },
                            )
                            session_id = session.session_id

                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "session_started",
                                        "session_id": session_id,
                                        "ai_greeting": "Hi! I'm Vortex. What would you like to talk about?",
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                )
                            )
                        except Exception as e:
                            logger.error(f"❌ Failed to start AI session: {e}")
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": f"Failed to start session: {str(e)}",
                                    }
                                )
                            )
                    else:
                        # Fallback without AI service
                        session_id = f"ws_session_{authenticated_user.id}_{datetime.utcnow().timestamp()}"
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "session_started",
                                    "session_id": session_id,
                                    "ai_greeting": "Hi! Welcome to VoiceApp! What topic would you like to discuss today?",
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                        )

                elif data.get("type") == "user_input":
                    # 🔴 BLOCK AI PROCESSING IF DISABLED
                    if not AI_PROCESSING_ENABLED:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "AI processing is currently disabled"
                        }))
                        continue
                    
                    user_text = data.get("text")
                    if not user_text:
                        await websocket.send_text(
                            json.dumps(
                                {"type": "error", "message": "Text input required"}
                            )
                        )
                        continue

                    logger.info(f"💬 Processing user input: {user_text}")
                    
                    # Use enhanced OpenAI service for conversation
                    try:
                        openai_service = container.get_openai_service()
                        
                        # Get user context for personalized conversation
                        user_context = {
                            "topics": [],  # Could be passed from frontend
                            "hashtags": [],
                            "transcription": user_text
                        }
                        
                        # Generate AI response with audio
                        response = await openai_service.realtime_conversation(
                            user_input=user_text,
                            conversation_context=[],  # Could maintain session history
                            user_context=user_context,
                            audio_response=True
                        )
                        
                        await websocket.send_text(json.dumps({
                            "type": "ai_response",
                            "text": response.get("response_text", "I understand!"),
                            "session_id": session_id,
                            "timestamp": response.get("timestamp")
                        }))
                        
                        # Send audio response if available
                        if "audio_data" in response:
                            await websocket.send_text(json.dumps({
                                "type": "audio_response",
                                "audio": response["audio_data"],
                                "format": response.get("audio_format", "mp3"),
                                "session_id": session_id
                            }))
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to process user input: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Failed to process input: {str(e)}"
                        }))

                # Handle audio input for streaming STT
                elif data.get("type") == "input_audio_buffer.append":
                    # 🔴 BLOCK AI PROCESSING IF DISABLED
                    if not AI_PROCESSING_ENABLED:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "AI processing is currently disabled"
                        }))
                        continue
                    
                    audio_data = data.get("audio")  # base64 encoded
                    if not audio_data:
                        await websocket.send_text(json.dumps({
                            "type": "error", 
                            "message": "Audio data required"
                        }))
                        continue
                        
                    try:
                        audio_bytes = base64.b64decode(audio_data)
                        
                        # Use streaming STT
                        openai_service = container.get_openai_service()
                        stt_result = await openai_service.streaming_speech_to_text(
                            audio_chunk=audio_bytes,
                            language="en-US"
                        )
                        
                        if stt_result.get("text"):
                            # Send transcription result
                            await websocket.send_text(json.dumps({
                                "type": "stt_result",
                                "text": stt_result["text"],
                                "confidence": stt_result.get("confidence", 0.0),
                                "language": stt_result.get("language", "en-US")
                            }))
                            
                            # Automatically process with AI if text is complete
                            user_text = stt_result["text"].strip()
                            if user_text and len(user_text.split()) >= 3:  # If substantial input
                                user_context = {
                                    "topics": [],
                                    "hashtags": [],
                                    "transcription": user_text
                                }
                                
                                response = await openai_service.realtime_conversation(
                                    user_input=user_text,
                                    user_context=user_context,
                                    audio_response=True
                                )
                                
                                await websocket.send_text(json.dumps({
                                    "type": "ai_response",
                                    "text": response.get("response_text", "I understand!"),
                                    "session_id": session_id,
                                    "timestamp": response.get("timestamp")
                                }))
                                
                                if "audio_data" in response:
                                    await websocket.send_text(json.dumps({
                                        "type": "audio_response",
                                        "audio": response["audio_data"],
                                        "format": response.get("audio_format", "mp3")
                                    }))
                        
                    except Exception as e:
                        logger.error(f"❌ Audio processing failed: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Audio processing failed: {str(e)}"
                        }))

                elif data.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        )
                    )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )

    except WebSocketDisconnect:
        logger.info("🎤 AI voice chat WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ AI voice chat WebSocket error: {e}")


# Real-time Audio Streaming WebSocket (NEW - for continuous voice input)
@router.websocket("/audio-stream")
async def websocket_audio_stream(websocket: WebSocket):
    """
    Real-time audio streaming WebSocket for GPT-4o Realtime API
    Uses proper async context manager for persistent connection
    
    Official OpenAI Realtime API Message Format:
    
    INPUT (Client → Server):
    {
      "type": "input_audio_buffer.append",
      "audio": "<Base64 encoded PCM16 audio string>"
    }
    
    OUTPUT Events (Server → Client):
    - "stt_done": Complete user speech transcription
    - "response.text.delta": AI text response streaming
    - "response.audio.delta": AI audio response streaming  
    - "audio_chunk": AI audio chunk (legacy compatibility)
    - "response.done": AI response completed
    - "ai_response_started": AI begins generating response
    - "audio_received": Server received audio chunk
    
    IMPORTANT: The OpenAI SDK expects base64 STRING, not raw bytes.
    Use: conn.input_audio_buffer.append(audio=base64_string)
    NOT: conn.input_audio_buffer.append(audio=raw_bytes)
    
    Legacy format still supported for backward compatibility:
    {
      "type": "audio_chunk", 
      "audio_data": "<Base64 encoded audio>"
    }
    """
    await websocket.accept()
    logger.info("🎙️ GPT-4o Realtime audio streaming WebSocket connected")
    
    authenticated_user = None
    openai_service = None
    session_context = {}
    
    try:
        # Handle authentication and initial setup
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle authentication
                if data.get("type") == "auth":
                    try:
                        token = data.get("token")
                        if not token:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "Authentication token required"
                            }))
                            continue
                            
                        # Verify Firebase token
                        from infrastructure.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
                        auth_middleware = FirebaseAuthMiddleware(container.get_user_repository())
                        decoded_token = auth_middleware.verify_firebase_token(token)
                        firebase_uid = decoded_token["uid"]
                        
                        user_repo = container.get_user_repository()
                        authenticated_user = user_repo.find_by_firebase_uid(firebase_uid)
                        
                        if not authenticated_user:
                            await websocket.send_text(json.dumps({
                                "type": "error", 
                                "message": "User not found"
                            }))
                            continue
                            
                        # Get OpenAI service
                        openai_service = container.get_openai_service()
                        if not openai_service:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "OpenAI service not available"
                            }))
                            continue
                            
                        await websocket.send_text(json.dumps({
                            "type": "authenticated",
                            "user_id": str(authenticated_user.id),
                            "display_name": authenticated_user.display_name
                        }))
                        
                    except Exception as e:
                        logger.error(f"❌ Authentication failed: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Authentication failed: {str(e)}"
                        }))
                        
                # Handle session start - Initialize GPT-4o Realtime connection and enter streaming loop
                elif data.get("type") == "start_session":
                    if not authenticated_user or not openai_service:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Must authenticate first"
                        }))
                        continue
                        
                    try:
                        # Extract user context from frontend
                        user_context = data.get("user_context", {})
                        topics = user_context.get("topics", [])
                        hashtags = user_context.get("hashtags", [])
                        transcription = user_context.get("transcription", "")
                        conversation_context = user_context.get("conversation_context", "")
                        
                        # Store session context
                        session_context = {
                            "user_id": str(authenticated_user.id),
                            "topics": topics,
                            "hashtags": hashtags,
                            "transcription": transcription,
                            "conversation_context": conversation_context
                        }
                        
                        logger.info(f"🤖 Starting GPT-4o Realtime session for user: {authenticated_user.id}")
                        logger.info(f"🎯 Session context: topics={topics}, hashtags={hashtags}")
                        
                        await websocket.send_text(json.dumps({
                            "type": "session_started",
                            "session_id": f"realtime_{authenticated_user.id}_{datetime.utcnow().timestamp()}",
                            "message": "GPT-4o Realtime session ready",
                            "context": session_context
                        }))
                        
                        # Start the persistent Realtime connection and streaming loop
                        await _handle_realtime_streaming(websocket, openai_service, session_context)
                        return  # Exit after streaming session ends
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to start Realtime session: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Session start failed: {str(e)}"
                        }))
                        
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info("🎤 GPT-4o Realtime audio streaming WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ GPT-4o Realtime audio streaming WebSocket error: {e}")


async def _handle_realtime_streaming(websocket: WebSocket, openai_service, session_context: dict):
    """
    Handle the persistent GPT-4o Realtime connection and streaming loop
    Uses proper async context manager for connection lifecycle
    """
    logger.info("🔗 Establishing persistent GPT-4o Realtime connection...")
    
    # Use proper async context manager for the Realtime connection
    async with openai_service.async_client.beta.realtime.connect(
        model="gpt-4o-realtime-preview"
    ) as conn:
        try:
            # Configure session ONCE with proper audio settings and SERVER-SIDE VAD
            # Following official OpenAI Realtime API pattern:
            # 1. Connect once
            # 2. Configure session once 
            # 3. Stream audio with input_audio_buffer.append(audio=bytes)
            # 4. Server VAD automatically handles turn detection
            # 5. Listen for response.audio.delta and response.text.delta events
            await conn.session.update(
                session={
                    "modalities": ["audio", "text"],
                    "voice": "shimmer",  # Choose voice: alloy, echo, fable, onyx, nova, shimmer
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16", 
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",  # 🔑 Use OpenAI's server-side VAD for automatic turn detection
                        "threshold": 0.5,      # Speech detection sensitivity: 0.0 (most sensitive) to 1.0 (least sensitive)
                        "prefix_padding_ms": 300,   # Audio milliseconds before speech to include
                        "silence_duration_ms": 500, # Silence duration before ending turn
                        "create_response": True,     # Automatically create response after turn ends
                        "interrupt_response": True   # Allow interrupting ongoing responses
                    }
                }
            )
            logger.info("✅ GPT-4o session configured with SERVER-SIDE VAD (pcm16, 24kHz expected)")
            logger.info("✅ GPT-4o session configured with audio I/O support")
            
            # Send system prompt ONCE
            topics = session_context.get("topics", [])
            hashtags = session_context.get("hashtags", [])
            conversation_context = session_context.get("conversation_context", "")
            transcription = session_context.get("transcription", "")
            
            system_prompt = f"""You are Vortex, a friendly AI conversation partner in a voice chat app.

Your role is to engage in natural conversation about topics the user is interested in.
Keep responses concise (1-3 sentences) and conversational.
Ask thoughtful questions to keep the discussion going.
Share relevant insights when appropriate.

Current conversation context:
{conversation_context}
"""

            await conn.conversation.item.create(
                item={
                    "type": "message",
                    "role": "system", 
                                            "content": [
                            {
                                "type": "input_text",
                                "text": system_prompt
                            }
                        ]
                }
            )
            
            logger.info("✅ GPT-4o Realtime session initialized, entering streaming loop...")
            
            # Server VAD Mode - continuous audio streaming
            logger.info("🎯 Using OpenAI server-side VAD - no manual utterance detection needed")
            
            # Start the event listener task for OpenAI Realtime events
            event_listener_task = asyncio.create_task(handle_realtime_events(conn, websocket, openai_service))
            
            # Main streaming loop - handle audio chunks and AI responses
            while True:
                try:
                    # Wait for WebSocket message (audio chunks or control messages)
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    message_type = data.get("type")
                    
                    # Handle audio streaming - support both legacy and official OpenAI formats
                    if message_type == "input_audio_buffer.append":
                        # 🔴 BLOCK AI PROCESSING IF DISABLED
                        if not AI_PROCESSING_ENABLED:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "AI processing is currently disabled"
                            }))
                            continue
                        
                        # Official OpenAI Realtime API format
                        audio_data = data.get("audio")  # base64 encoded
                        if audio_data:
                            # logger.info(f"📥 [OpenAI-Official] Streaming audio to OpenAI: {len(audio_data)} base64 chars")  # COMMENTED OUT - too verbose
                            
                            try:
                                # Official OpenAI Realtime API pattern: pass base64 string directly
                                # SDK expects base64 string, not raw bytes
                                await conn.input_audio_buffer.append(audio=audio_data)
                                
                                # Send acknowledgment using OpenAI format
                                await websocket.send_text(json.dumps({
                                    "type": "input_audio_buffer.appended",
                                    "message": "Audio appended to buffer"
                                }))
                                
                            except Exception as e:
                                logger.error(f"❌ [OpenAI-Official] Audio processing failed: {e}")
                    
                    elif message_type == "audio_chunk":
                        # 🔴 BLOCK AI PROCESSING IF DISABLED
                        if not AI_PROCESSING_ENABLED:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "AI processing is currently disabled"
                            }))
                            continue
                        
                        # Legacy format for backward compatibility
                        audio_data = data.get("audio_data")  # base64 encoded
                        if audio_data:
                            # logger.info(f"📥 [Legacy] Streaming audio chunk to OpenAI: {len(audio_data)} base64 chars")  # COMMENTED OUT - too verbose
                            
                            try:
                                # Convert legacy format to official OpenAI method
                                # Pass base64 string directly, no decoding needed
                                await conn.input_audio_buffer.append(audio=audio_data)
                                
                                # Send acknowledgment
                                await websocket.send_text(json.dumps({
                                    "type": "audio_received",
                                    "message": "Audio streamed to server VAD"
                                }))
                                
                            except Exception as e:
                                logger.error(f"❌ [Legacy] Audio processing failed: {e}")
                    
                    elif message_type == "utterance_end":
                        # With server VAD, utterance_end is not needed - log for debugging
                        logger.info("📥 [ServerVAD] Received utterance_end (not needed with server VAD)")
                        await websocket.send_text(json.dumps({
                            "type": "utterance_processed", 
                            "message": "Server VAD handles turn detection automatically"
                        }))
                        
                    elif message_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    
                except WebSocketDisconnect:
                    logger.info("🎤 Client disconnected from streaming session")
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    logger.error(f"❌ Error in streaming loop: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Streaming error: {str(e)}"
                    }))
            
            # Cancel the event listener task when the main loop ends
            event_listener_task.cancel()
            try:
                await event_listener_task
            except asyncio.CancelledError:
                logger.info("🧹 Event listener task cancelled")
                    
        except Exception as e:
            logger.error(f"❌ Realtime connection error: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            }))
        finally:
            logger.info("🧹 GPT-4o Realtime connection will be closed by context manager")


async def handle_realtime_events(conn, websocket: WebSocket, openai_service):
    """
    Handle OpenAI Realtime API events and forward them to the WebSocket client
    This runs in the background while audio is being streamed
    """
    logger.info("🎧 Starting OpenAI Realtime event listener...")
    
    try:
        async for event in conn:
            event_type = event.type
            # logger.info(f"📨 [RealtimeEvent] {event_type}")  # COMMENTED OUT - too verbose
            
            # Handle different types of events
            if event_type == "conversation.item.input_audio_transcription.completed":
                # User's speech has been transcribed
                transcription = event.transcript
                logger.info(f"📝 [Transcription] User said: '{transcription}'")
                
                await websocket.send_text(json.dumps({
                    "type": "stt_done",  # Fix: Change to the event type expected by the frontend
                    "text": transcription,
                    "confidence": 0.95,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "response.text.delta":
                # Streaming text response from AI
                text_delta = event.delta
                logger.info(f"📝 [AI Text] Delta: '{text_delta}'")
                
                await websocket.send_text(json.dumps({
                    "type": "response.text.delta",  # Fix: Use the correct AI text response event type
                    "delta": text_delta,  # Use delta field name to match frontend expectations
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "response.audio.delta":
                # Streaming audio response from AI
                audio_delta = event.delta
                # logger.info(f"🎵 [AI Audio] Delta received - type: {type(audio_delta)}, size: {len(audio_delta) if audio_delta else 0}")  # COMMENTED OUT - too verbose
                
                try:
                    # Convert audio_delta to bytes if it's a string
                    if isinstance(audio_delta, str):
                        try:
                            # Try to decode as base64 first
                            pcm_bytes = base64.b64decode(audio_delta)
                            # logger.info(f"🎵 [AI Audio] Decoded base64 to {len(pcm_bytes)} bytes")  # COMMENTED OUT - too verbose
                        except Exception as decode_error:
                            # If not valid base64, try encoding as UTF-8
                            pcm_bytes = audio_delta.encode("utf-8")
                            logger.warning(f"🎵 [AI Audio] Not base64, encoded as UTF-8: {len(pcm_bytes)} bytes")
                    else:
                        pcm_bytes = audio_delta  # Already bytes
                        # logger.info(f"🎵 [AI Audio] Already bytes: {len(pcm_bytes)} bytes")  # COMMENTED OUT - too verbose
                    
                    # Convert PCM16 to WAV and send to client
                    wav_audio = openai_service._pcm16_to_wav(pcm_bytes)
                    await websocket.send_text(json.dumps({
                        "type": "audio_chunk",
                        "audio": base64.b64encode(wav_audio).decode("utf-8"),
                        "format": "wav"
                    }))
                    
                    # Also send the raw delta format for direct handling
                    await websocket.send_text(json.dumps({
                        "type": "response.audio.delta",
                        "delta": base64.b64encode(wav_audio).decode("utf-8"),
                        "format": "wav"
                    }))
                    
                except Exception as audio_error:
                    logger.error(f"❌ [AI Audio] Processing failed: {audio_error}")
                    logger.error(f"❌ [AI Audio] audio_delta type: {type(audio_delta)}, content: {str(audio_delta)[:100]}...")
                
            elif event_type == "response.done":
                # AI response completed
                logger.info("✅ [AI] Response completed")
                await websocket.send_text(json.dumps({
                    "type": "response.done",  # Fix: Change to the event type expected by the frontend
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "conversation.item.created":
                # New conversation item (audio) added
                # logger.info("📥 [Conversation] New audio item added to conversation")  # COMMENTED OUT - too verbose
                pass
                
            elif event_type == "input_audio_buffer.speech_started":
                # Server VAD detected speech start
                logger.info("🎤 [ServerVAD] Speech started")
                await websocket.send_text(json.dumps({
                    "type": "speech_started",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "input_audio_buffer.speech_stopped":
                # Server VAD detected speech end
                logger.info("🔇 [ServerVAD] Speech stopped")
                await websocket.send_text(json.dumps({
                    "type": "speech_stopped",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "input_audio_buffer.committed":
                # Audio buffer committed (for manual mode)
                # logger.info("📝 [ServerVAD] Audio buffer committed")  # COMMENTED OUT - too verbose
                pass
                
            elif event_type == "response.output_item.added":
                # New output item added to response
                # logger.info("📤 [Response] Output item added")  # COMMENTED OUT - too verbose
                pass
                
            elif event_type == "response.content_part.added":
                # New content part added
                # logger.info("📝 [Response] Content part added")  # COMMENTED OUT - too verbose
                pass
                
            elif event_type == "response.created":
                # AI response started
                logger.info("🤖 [AI] Response started")
                await websocket.send_text(json.dumps({
                    "type": "ai_response_started",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type == "error":
                # Handle errors
                logger.error(f"❌ [RealtimeAPI] Error: {event}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Realtime API error: {str(event)}",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
            elif event_type in ["response.audio_transcript.delta"]:
                # Audio transcript deltas - too verbose, skip logging
                pass
                
            else:
                # Log other event types for debugging only if not common/verbose events
                if event_type not in ["response.audio_transcript.delta", "response.audio_transcript.done"]:
                    # logger.info(f"📋 [RealtimeEvent] Other: {event_type}")  # COMMENTED OUT - too verbose
                    pass
                
    except Exception as e:
        logger.error(f"❌ Error in event listener: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Event listener error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }))


async def process_ai_response(websocket: WebSocket, user_text: str, session_id: str):
    """
    Legacy function for processing AI responses via separate HTTP calls
    Note: Now replaced by persistent GPT-4o Realtime connection in /audio-stream
    This function is kept for compatibility with other WebSocket endpoints
    """
    try:
        logger.info(f"🤖 Processing AI response for: '{user_text[:50]}...'")
        
        # Get OpenAI service
        openai_service = container.get_openai_service()
        if not openai_service:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "OpenAI service not available"
            }))
            return
        
        # Build user context for conversation
        user_context = {
            "topics": [],  # Could extract from user_text
            "hashtags": [],
            "transcription": user_text,
            "session_id": session_id
        }
        
        # Use GPT-4o Realtime for AI conversation
        response = await openai_service.realtime_conversation(
            user_input=user_text,
            conversation_context=[],
            user_context=user_context,
            audio_response=True
        )
        
        # Send text response
        await websocket.send_text(json.dumps({
            "type": "ai_response",
            "text": response.get("response_text", "I understand!"),
            "session_id": session_id,
            "timestamp": response.get("timestamp", datetime.utcnow().isoformat())
        }))
        
        # Send audio response if available
        if "audio_data" in response:
            await websocket.send_text(json.dumps({
                "type": "audio_response", 
                "audio": response["audio_data"],
                "format": response.get("audio_format", "wav"),
                "session_id": session_id
            }))
            
        logger.info(f"✅ AI response sent for session: {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to process AI response: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"AI response failed: {str(e)}",
            "session_id": session_id
        }))


# Health Check
@router.get("/health")
async def ai_host_health_check(openai_service=Depends(get_openai_service)):
    """
    Check AI host service health
    """
    try:
        # Check OpenAI connectivity
        if openai_service:
            openai_health = openai_service.health_check()
        else:
            openai_health = {
                "status": "unavailable",
                "error": "OpenAI service not initialized",
            }

        return {
            "status": "healthy" if openai_health["status"] == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {"openai": openai_health["status"], "ai_host": "active"},
            "features": {
                "tts": True,
                "stt": True,
                "topic_extraction": True,
                "conversation_hosting": True,
            },
        }

    except Exception as e:
        logger.error(f"❌ AI host health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
