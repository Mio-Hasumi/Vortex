"""
AI Host API routes for VoiceApp

Provides endpoints for AI-driven conversation hosting:
- Text-to-Speech (TTS) for AI voice
- Real-time subtitles via WebSocket
- Topic extraction and hashtag generation
- AI conversation management
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import io
import logging
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
    ai_host_service = Depends(get_ai_host_service),
    current_user: User = Depends(get_current_user)
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
            "preferences": request.user_preferences or {}
        }
        
        # Start AI host session
        session = await ai_host_service.start_session(
            user_id=current_user.id,
            user_context=user_context
        )
        
        # Get the AI greeting from conversation history
        ai_greeting = "Hi! Welcome to VoiceApp! What topic would you like to discuss today?"
        if session.conversation_history:
            ai_greeting = session.conversation_history[-1]["message"]
        
        return StartSessionResponse(
            session_id=session.session_id,
            ai_greeting=ai_greeting,
            session_state=session.state
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start AI session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start AI session: {str(e)}"
        )

@router.post("/process-input", response_model=ProcessInputResponse)
async def process_user_input(
    request: ProcessInputRequest,
    ai_host_service = Depends(get_ai_host_service),
    current_user: User = Depends(get_current_user)
):
    """
    Process user input and get AI host response
    """
    try:
        logger.info(f"🎙️ Processing user input for session: {request.session_id}")
        
        # Process user input through AI host
        response_data = await ai_host_service.process_user_input(
            session_id=request.session_id,
            user_input=request.user_input
        )
        
        return ProcessInputResponse(
            session_id=request.session_id,
            ai_response=response_data.get("response_text", ""),
            session_state=response_data.get("session_state", "unknown"),
            extracted_topics=response_data.get("extracted_topics", []),
            generated_hashtags=response_data.get("generated_hashtags", []),
            next_action=response_data.get("next_action")
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to process user input: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process input: {str(e)}"
        )

# Text-to-Speech Endpoints (Urgently needed by frontend!)
@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    openai_service = Depends(get_openai_service)
):
    """
    Convert text to speech using OpenAI TTS
    This endpoint can be called directly by the frontend to obtain AI voice
    """
    try:
        logger.info(f"🔊 TTS request for text: '{request.text[:50]}...'")
        
        # Debug: Check if text_to_speech is a coroutine function
        import inspect
        logger.info(f"🔍 is coroutine? {inspect.iscoroutinefunction(openai_service.text_to_speech)}")
        
        # Generate TTS audio
        audio_bytes = await openai_service.text_to_speech(
            text=request.text,
            voice=request.voice,
            speed=request.speed
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
                "Content-Length": str(len(audio_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}"
        )

@router.get("/tts/{text}")
async def text_to_speech_get(
    text: str,
    voice: str = "nova",
    speed: float = 1.0,
    openai_service = Depends(get_openai_service)
):
    """
    GET endpoint for TTS (convenient for frontend)
    Usage: /api/ai-host/tts/HelloWorld?voice=nova&speed=1.0
    """
    try:
        # Generate TTS audio
        audio_bytes = await openai_service.text_to_speech(
            text=text,
            voice=voice,
            speed=speed
        )
        
        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename=tts_{text[:10]}.mp3"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ TTS GET failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}"
        )

# Topic Extraction (Urgently needed by frontend!)
@router.post("/extract-topics", response_model=TopicExtractionResponse)
async def extract_topics(
    request: TopicExtractionRequest,
    current_user: User = Depends(get_current_user)
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
                detail="OpenAI service not available"
            )
        
        logger.info(f"🧠 Extracting topics from: '{request.text[:100]}...'")
        
        # Extract topics and hashtags using GPT-4
        result = await openai_service.extract_topics_and_hashtags(
            text=request.text,
            context=request.user_context.model_dump() if request.user_context else {},
            language="en-US"
        )
        
        return TopicExtractionResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Topic extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topic extraction failed: {str(e)}"
        )

@router.post("/extract-topics-from-voice", response_model=VoiceTopicExtractionResponse)
async def extract_topics_from_voice(
    audio_file: UploadFile = File(...),
    language: str = Form("en-US"),
    current_user: User = Depends(get_current_user)
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
                detail="OpenAI service not available"
            )
        
        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file"
            )
        
        # Read audio content
        audio_content = await audio_file.read()
        
        # Check file size (max 25MB)
        if len(audio_content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file too large. Maximum size is 25MB."
            )
        
        logger.info(f"🎙️ Processing voice input for topic extraction: {len(audio_content)/1024/1024:.2f}MB")
        
        # Process voice to extract topics and hashtags
        result = await openai_service.process_voice_for_hashtags(
            audio_data=audio_content,
            audio_format=audio_file.content_type.split('/')[-1],
            language=language
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return VoiceTopicExtractionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Voice topic extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice topic extraction failed: {str(e)}"
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
    openai_service = Depends(get_openai_service),
    current_user: User = Depends(get_current_user)
):
    """
    Upload audio file for speech-to-text transcription
    
    Core user workflow: User registers and directly uploads speech saying what they want to talk about
    """
    try:
        logger.info(f"🎙️ Processing audio upload for user: {current_user.id}")
        logger.info(f"📁 File: {audio_file.filename}, type: {audio_file.content_type}")
        
        # Validate file type
        allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/m4a", "audio/ogg"]
        if audio_file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Allowed: {', '.join(allowed_types)}"
            )
        
        # Check file size (max 25MB for OpenAI Whisper)
        max_size = 25 * 1024 * 1024  # 25MB
        audio_content = await audio_file.read()
        if len(audio_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file too large. Maximum size is 25MB."
            )
        
        logger.info(f"📏 Audio file size: {len(audio_content)/1024/1024:.2f}MB")
        
        # Create BytesIO object for OpenAI API
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = audio_file.filename or "audio.mp3"
        
        # Perform STT using OpenAI Whisper
        stt_result = await openai_service.speech_to_text(
            audio_file=audio_buffer,
            language=language
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
                        "language": stt_result.get("language", "en-US")
                    }
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
            generated_hashtags=generated_hashtags
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Audio upload STT failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio processing failed: {str(e)}"
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
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Live subtitle service ready",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
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
                        "duration": len(data.get("text", "")) * 0.1  # Rough estimate
                    }
                    
                    await websocket.send_text(json.dumps(subtitle_data))
                    
                elif data.get("type") == "audio":
                    # Process audio for real-time STT and subtitle generation
                    try:
                        audio_data = data.get("audio_data")  # base64 encoded audio
                        if audio_data:
                            # Decode base64 audio data
                            import base64
                            audio_bytes = base64.b64decode(audio_data)
                            
                            # Create audio buffer for STT
                            audio_buffer = io.BytesIO(audio_bytes)
                            audio_buffer.name = "realtime_audio.wav"
                            
                            # Get OpenAI service instance
                            openai_service = container.get_openai_service()
                            
                            # Perform STT
                            stt_result = await openai_service.speech_to_text(
                                audio_file=audio_buffer,
                                language=data.get("language", "en-US")
                            )
                            
                            # Send subtitle with transcription
                            await websocket.send_text(json.dumps({
                                "type": "subtitle",
                                "text": stt_result["text"],
                                "language": stt_result.get("language", "unknown"),
                                "confidence": stt_result.get("confidence", 0.0),
                                "timestamp": datetime.utcnow().isoformat()
                            }))
                            
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "No audio data provided"
                            }))
                            
                    except Exception as e:
                        logger.error(f"❌ Real-time STT failed: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "subtitle",
                            "text": "[Speech recognition failed]",
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                
                elif data.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info("🎬 Live subtitle WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ Live subtitle WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error", 
                "message": str(e)
            }))
        except:
            pass

# Voice Chat WebSocket (Complete AI Host Interaction)
@router.websocket("/voice-chat")
async def websocket_voice_chat(websocket: WebSocket):
    """
    WebSocket endpoint for full AI host voice interaction
    Supports full process of voice input, AI processing, and TTS output
    """
    try:
        await websocket.accept()
        logger.info("🎤 AI voice chat WebSocket connected")
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "AI voice chat ready",
            "ai_greeting": "Hi! Welcome to VoiceApp! What topic would you like to discuss today?",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        session_id = None
        
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "start_session":
                    # Start AI host session
                    # TODO: Get user from WebSocket auth
                    user_id = UUID(data.get("user_id"))  # Temporary, should use auth
                    
                    # Start session (simplified)
                    session_id = f"ws_session_{user_id}_{datetime.utcnow().timestamp()}"
                    
                    await websocket.send_text(json.dumps({
                        "type": "session_started",
                        "session_id": session_id,
                        "ai_greeting": "Hi! Welcome to VoiceApp! What topic would you like to discuss today?",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif data.get("type") == "user_input":
                    if not session_id:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "No active session. Please start a session first."
                        }))
                        continue
                    
                    user_text = data.get("text", "")
                    
                    # TODO: Process through AI host service
                    # For now, send a simple echo response
                    await websocket.send_text(json.dumps({
                        "type": "ai_response",
                        "text": f"I heard you say: {user_text}. This is interesting!",
                        "session_id": session_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info("🎤 AI voice chat WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ AI voice chat WebSocket error: {e}")

# Health Check
@router.get("/health")
async def ai_host_health_check(
    openai_service = Depends(get_openai_service)
):
    """
    Check AI host service health
    """
    try:
        # Check OpenAI connectivity
        if openai_service:
            openai_health = openai_service.health_check()
        else:
            openai_health = {"status": "unavailable", "error": "OpenAI service not initialized"}
        
        return {
            "status": "healthy" if openai_health["status"] == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "openai": openai_health["status"],
                "ai_host": "active"
            },
            "features": {
                "tts": True,
                "stt": True,
                "topic_extraction": True,
                "conversation_hosting": True
            }
        }
        
    except Exception as e:
        logger.error(f"❌ AI host health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 