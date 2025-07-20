"""
AI Host API routes for VoiceApp

Provides endpoints for AI-driven conversation hosting:
- Text-to-Speech (TTS) for AI voice
- Real-time subtitles via WebSocket
- Topic extraction and hashtag generation
- AI conversation management
"""

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
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import io
import logging
import base64
from datetime import datetime

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import User

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

        # Get the AI greeting from conversation history
        ai_greeting = (
            "Hi! Welcome to VoiceApp! What topic would you like to discuss today?"
        )
        if session.conversation_history:
            ai_greeting = session.conversation_history[-1]["message"]

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
            detail=f"TTS generation failed: {str(e)}",
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
    Extract topics and hashtags from text input using GPT-4

    This endpoint analyzes text and extracts:
    - Main topics (3-5 key topics)
    - Relevant hashtags (5-8 hashtags for matching)
    - Content category
    - Sentiment analysis
    - Conversation style
    """
    try:
        openai_service = container.get_openai_service()
        if not openai_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service not available",
            )

        logger.info(f"🧠 Extracting topics from: '{request.text[:100]}...'")

        # Extract topics and hashtags using GPT-4
        result = await openai_service.extract_topics_and_hashtags(
            text=request.text,
            context=request.user_context if request.user_context else {},
            language="en-US",
        )

        return TopicExtractionResponse(**result)

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
    Extract topics and hashtags from voice input using Whisper + GPT-4

    This endpoint processes voice input and extracts:
    - Speech transcription (using Whisper)
    - Main topics (using GPT-4)
    - Relevant hashtags for matching
    - Content analysis (sentiment, style, category)

    The voice-to-hashtag pipeline:
    Voice → Whisper STT → GPT-4 Topic Analysis → Hashtags for Matching
    """
    try:
        openai_service = container.get_openai_service()
        if not openai_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service not available",
            )

        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith(
            "audio/"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file",
            )

        # Read audio content
        audio_content = await audio_file.read()

        # Check file size (max 25MB)
        if len(audio_content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file too large. Maximum size is 25MB.",
            )

        logger.info(
            f"🎙️ Processing voice input for topic extraction: {len(audio_content)/1024/1024:.2f}MB"
        )

        # Process voice to extract topics and hashtags
        result = await openai_service.process_voice_for_hashtags(
            audio_data=audio_content,
            audio_format=audio_file.content_type.split("/")[-1],
            language=language,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
            )

        return VoiceTopicExtractionResponse(**result)

    except HTTPException:
        raise
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
    Upload audio file for speech-to-text transcription

    Core user workflow: User registers and directly uploads speech saying what they want to talk about
    """
    try:
        logger.info(f"🎙️ Processing audio upload for user: {current_user.id}")
        logger.info(f"📁 File: {audio_file.filename}, type: {audio_file.content_type}")

        # Critical: Check if OpenAI service is available
        if openai_service is None:
            logger.error("❌ OpenAI service is not available - check OPENAI_API_KEY configuration")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Speech-to-text service is not available. Please check server configuration."
            )
        
        logger.info("✅ OpenAI service is available, proceeding with audio processing")

        # Validate file type
        allowed_types = [
            "audio/wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/m4a",
            "audio/ogg",
        ]
        if audio_file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Allowed: {', '.join(allowed_types)}",
            )

        # Check file size (max 25MB for OpenAI Whisper)
        max_size = 25 * 1024 * 1024  # 25MB
        audio_content = await audio_file.read()
        if len(audio_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file too large. Maximum size is 25MB.",
            )

        logger.info(f"📏 Audio file size: {len(audio_content)/1024/1024:.2f}MB")

        # Create BytesIO object for OpenAI API
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = audio_file.filename or "audio.mp3"

        # Perform STT using OpenAI Whisper
        stt_result = await openai_service.speech_to_text(
            audio_file=audio_buffer, language=language
        )

        transcription = stt_result["text"]
        logger.info(f"✅ STT completed: '{transcription[:100]}...'")

        # Optional: Extract topics and hashtags
        extracted_topics = None
        generated_hashtags = None

        if extract_topics and transcription.strip():
            try:
                topic_data = await openai_service.extract_topics_and_hashtags(
                    text=transcription,
                    context={
                        "user_id": str(current_user.id),
                        "source": "voice_upload",
                        "language": stt_result.get("language", "en-US"),
                    },
                )

                extracted_topics = topic_data.get("main_topics", [])
                generated_hashtags = topic_data.get("hashtags", [])

                logger.info(f"🏷️ Extracted hashtags: {generated_hashtags}")

            except Exception as e:
                logger.warning(f"⚠️ Topic extraction failed, but STT succeeded: {e}")

        return STTResponse(
            transcription=transcription,
            language=stt_result.get("language", "unknown"),
            duration=stt_result.get("duration", 0.0),
            confidence=stt_result.get("confidence", 0.0),
            words=stt_result.get("words", []),
            extracted_topics=extracted_topics,
            generated_hashtags=generated_hashtags,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Audio upload STT failed: {e}")
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
                                        "ai_greeting": "Hi! Welcome to VoiceApp! What topic would you like to discuss today?",
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
            # Configure session ONCE with proper audio settings
            await conn.session.update(
                session={
                    "modalities": ["audio", "text"],
                    "voice": "shimmer",  # Choose voice: alloy, echo, fable, onyx, nova, shimmer
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"}
                }
            )
            logger.info("✅ GPT-4o session configured with audio I/O support")
            
            # Send system prompt ONCE
            topics = session_context.get("topics", [])
            hashtags = session_context.get("hashtags", [])
            conversation_context = session_context.get("conversation_context", "")
            transcription = session_context.get("transcription", "")
            
            system_prompt = f"""You are a friendly AI conversation partner in a voice chat app. 

User context:
- Topics of interest: {', '.join(topics) if topics else 'General conversation'}
- Hashtags: {', '.join(hashtags) if hashtags else 'None'}
- Previous conversation: {conversation_context if conversation_context else 'First interaction'}
- User background: {transcription if transcription else 'No additional context'}

Guidelines:
- Respond naturally and conversationally
- Keep responses concise but engaging (1-3 sentences)
- Ask follow-up questions to encourage dialogue
- Stay focused on the user's interests
- Use natural speech patterns suitable for voice chat"""

            await conn.conversation.item.create(
                item={
                    "type": "message",
                    "role": "system", 
                    "content": system_prompt
                }
            )
            
            logger.info("✅ GPT-4o Realtime session initialized, entering streaming loop...")
            
            # Audio accumulation state
            accumulated_audio_chunks = []
            is_accumulating = False
            
            # Main streaming loop - handle audio chunks and responses
            while True:
                try:
                    # Wait for WebSocket message
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    message_type = data.get("type")
                    
                    if message_type == "audio_chunk":
                        audio_data = data.get("audio_data")  # base64 encoded
                        if audio_data:
                            logger.info("🎵 Accumulating audio chunk...")
                            
                            # Accumulate audio chunks instead of processing each individually
                            accumulated_audio_chunks.append(audio_data)
                            is_accumulating = True
                            
                            # Send acknowledgment
                            await websocket.send_text(json.dumps({
                                "type": "audio_received",
                                "chunks_accumulated": len(accumulated_audio_chunks)
                            }))
                    
                    elif message_type == "utterance_end":
                        if accumulated_audio_chunks and is_accumulating:
                            logger.info(f"🎯 Processing complete utterance with {len(accumulated_audio_chunks)} chunks...")
                            
                            # Combine all accumulated audio chunks
                            # For now, we'll process them as separate items, but could be combined
                            for i, audio_chunk in enumerate(accumulated_audio_chunks):
                                await conn.conversation.item.create(
                                    item={
                                        "type": "message",
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "input_audio",
                                                "input_audio": {"data": audio_chunk, "format": "wav"}
                                            }
                                        ]
                                    }
                                )
                            
                            # NOW request AI response (only after complete utterance)
                            logger.info("🤖 Requesting AI response for complete utterance...")
                            await conn.response.create()
                            
                            # Process streaming response from same connection
                            text_chunks = []
                            audio_chunks = []
                            event_count = 0
                            
                            logger.info("🔗 Starting to listen for GPT-4o Realtime events...")
                            async for event in conn:
                                event_count += 1
                                logger.info(f"📨 Event #{event_count}: {event.type}")
                                
                                if event.type == "response.text.delta":
                                    text_chunks.append(event.delta)
                                    logger.info(f"📝 Text delta: '{event.delta}' (total chunks: {len(text_chunks)})")
                                    # Send partial text for real-time display
                                    await websocket.send_text(json.dumps({
                                        "type": "stt_chunk",
                                        "text": event.delta,
                                        "confidence": 0.95,
                                        "timestamp": datetime.utcnow().isoformat()
                                    }))
                                elif event.type == "response.audio.delta":
                                    audio_chunks.append(event.delta)
                                    logger.info(f"🎵 Audio delta received: {len(event.delta)} bytes (total chunks: {len(audio_chunks)})")
                                    
                                    # Convert PCM16 to WAV and send real-time audio chunks to client
                                    wav_audio = openai_service._pcm16_to_wav(event.delta)
                                    await websocket.send_text(json.dumps({
                                        "type": "audio_chunk",
                                        "audio": base64.b64encode(wav_audio).decode("utf-8"),
                                        "format": "wav"
                                    }))
                                elif event.type == "response.done":
                                    logger.info("✅ Response done event received")
                                    break
                                elif event.type == "error":
                                    logger.error(f"❌ GPT-4o Realtime error: {event}")
                                    break
                                else:
                                    logger.info(f"📋 Other event: {event.type}")
                            
                            logger.info(f"🏁 Event loop finished. Total events: {event_count}, text chunks: {len(text_chunks)}, audio chunks: {len(audio_chunks)}")
                            
                            # Send complete responses
                            full_text = "".join(text_chunks)
                            full_audio = b"".join(audio_chunks) if audio_chunks else None
                            
                            logger.info(f"📊 Final aggregation - text length: {len(full_text)}, audio bytes: {len(full_audio) if full_audio else 0}")
                            
                            if full_text:
                                await websocket.send_text(json.dumps({
                                    "type": "ai_response",
                                    "text": full_text,
                                    "timestamp": datetime.utcnow().isoformat()
                                }))
                                logger.info(f"✅ AI response sent: {len(full_text)} chars")
                            else:
                                logger.warning("⚠️ No text response generated by GPT-4o Realtime")
                            
                            if full_audio:
                                # Convert PCM16 to WAV format for iOS compatibility
                                wav_audio = openai_service._pcm16_to_wav(full_audio)
                                await websocket.send_text(json.dumps({
                                    "type": "audio_response",
                                    "audio": base64.b64encode(wav_audio).decode("utf-8"),
                                    "format": "wav"
                                }))
                                logger.info(f"✅ AI audio sent: {len(full_audio)} bytes")
                            else:
                                logger.warning("⚠️ No audio response generated by GPT-4o Realtime")
                            
                            # If no response was generated, try fallback to ChatCompletion
                            if not full_text:
                                logger.info("🔄 Attempting ChatCompletion fallback...")
                                try:
                                    # Generate text response using ChatCompletion as fallback
                                    topics = session_context.get("topics", [])
                                    hashtags = session_context.get("hashtags", [])
                                    
                                    fallback_prompt = f"""You are a friendly AI conversation partner. The user is interested in: {', '.join(topics) if topics else 'general conversation'}.
                                    
Hashtags: {', '.join(hashtags) if hashtags else 'none'}

Respond naturally and conversationally to continue the discussion. Keep it brief and engaging (1-2 sentences)."""

                                    response = await openai_service.async_client.chat.completions.create(
                                        model="gpt-4o",
                                        messages=[
                                            {"role": "system", "content": fallback_prompt},
                                            {"role": "user", "content": "Hi! Let's talk about these topics."}
                                        ],
                                        max_tokens=150
                                    )
                                    
                                    fallback_text = response.choices[0].message.content
                                    logger.info(f"✅ Fallback response generated: {len(fallback_text)} chars")
                                    
                                    await websocket.send_text(json.dumps({
                                        "type": "ai_response",
                                        "text": fallback_text,
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "source": "fallback"
                                    }))
                                    
                                except Exception as fallback_error:
                                    logger.error(f"❌ Fallback also failed: {fallback_error}")
                                    await websocket.send_text(json.dumps({
                                        "type": "ai_response", 
                                        "text": f"Hi! I'm excited to chat with you about {', '.join(topics) if topics else 'whatever interests you'}! What would you like to discuss?",
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "source": "hardcoded_fallback"
                                    }))
                            
                            # Reset accumulation state
                            accumulated_audio_chunks = []
                            is_accumulating = False
                        
                        else:
                            # Acknowledge utterance end even if no audio
                            await websocket.send_text(json.dumps({
                                "type": "utterance_processed",
                                "message": "No audio to process"
                            }))
                        
                    elif message_type == "silence_detected":
                        # Auto-trigger utterance_end on silence
                        logger.info("🔇 Silence detected, auto-processing utterance...")
                        if accumulated_audio_chunks and is_accumulating:
                            # Trigger the same logic as utterance_end
                            data["type"] = "utterance_end"
                            continue  # Re-process this message as utterance_end
                        
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
                    
        except Exception as e:
            logger.error(f"❌ Realtime connection error: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            }))
        finally:
            logger.info("🧹 GPT-4o Realtime connection will be closed by context manager")


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
