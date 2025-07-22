"""
Rooms API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import asyncio
import json
import logging
from datetime import datetime

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import RoomStatus, User, Room
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class RoomResponse(BaseModel):
    id: str
    name: str
    topic: str
    participants: List[str]
    max_participants: int
    status: str
    created_at: str
    livekit_room_name: str
    livekit_token: str

class ParticipantResponse(BaseModel):
    user_id: str
    display_name: str
    joined_at: str
    is_speaking: bool
    connection_quality: str

class RoomListResponse(BaseModel):
    rooms: List[RoomResponse]
    total: int

class JoinRoomRequest(BaseModel):
    room_id: str

class CreateRoomRequest(BaseModel):
    name: str
    topic: str
    max_participants: int = 10
    is_private: bool = False

# Dependency injection
def get_room_repository():
    return container.get_room_repository()

def get_user_repository():
    return container.get_user_repository()

def get_topic_repository():
    return container.get_topic_repository()

# Helper functions
def get_topic_name(topic_id: UUID, topic_repo) -> str:
    """Get topic name by ID, fallback to 'General' if not found"""
    try:
        topic = topic_repo.find_by_id(topic_id)
        return topic.name if topic else "General"
    except:
        return "General"

# Helper function to create a room for API
def create_room_entity(name: str, topic: str, created_by: UUID, max_participants: int = 10, is_private: bool = False) -> Room:
    """Create a room entity for API usage"""
    room_id = uuid4()
    # For now, we'll use a generated UUID for topic_id
    # In a real implementation, you would lookup the topic by name
    topic_id = uuid4()
    
    return Room(
        id=room_id,
        name=name,
        topic_id=topic_id,
        livekit_room_name=f"room_{room_id}",
        host_ai_identity=f"ai_host_{room_id}",
        max_participants=max_participants,
        created_by=created_by,
        is_private=is_private
    )

# Room endpoints
@router.post("/", response_model=RoomResponse)
async def create_room(
    request: CreateRoomRequest,
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new voice chat room
    """
    try:
        current_user_id = current_user.id
        
        # Create room entity
        room = create_room_entity(
            name=request.name,
            topic=request.topic,
            created_by=current_user_id,
            max_participants=request.max_participants,
            is_private=request.is_private
        )
        
        # Save to repository
        saved_room = await room_repo.save(room)
        
        return RoomResponse(
            id=str(saved_room.id),
            name=saved_room.name,
            topic=request.topic,  # Use original topic string
            participants=[str(p) for p in saved_room.current_participants],
            max_participants=saved_room.max_participants,
            status=saved_room.status.name.lower(),
            created_at=saved_room.created_at.isoformat(),
            livekit_room_name=saved_room.livekit_room_name,
            livekit_token=room_repo.generate_livekit_token(saved_room.id, current_user_id)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/join", response_model=RoomResponse)
async def join_room(
    request: JoinRoomRequest,
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Join an existing room
    """
    try:
        room_id = UUID(request.room_id)
        current_user_id = current_user.id
        
        # Check if room exists
        room = room_repo.find_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Add user to room
        if not room_repo.add_participant(room_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to join room (room might be full)"
            )
        
        # Get updated room info
        updated_room = room_repo.find_by_id(room_id)
        
        # Get topic repository for topic name lookup
        topic_repo = container.get_topic_repository()
        
        return RoomResponse(
            id=str(updated_room.id),
            name=updated_room.name,
            topic=get_topic_name(updated_room.topic_id, topic_repo),
            participants=[str(p) for p in updated_room.current_participants],
            max_participants=updated_room.max_participants,
            status=updated_room.status.name.lower(),
            created_at=updated_room.created_at.isoformat(),
            livekit_room_name=updated_room.livekit_room_name,
            livekit_token=room_repo.generate_livekit_token(room_id, current_user_id)
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Leave a room
    """
    try:
        room_uuid = UUID(room_id)
        current_user_id = current_user.id
        
        # Check if room exists
        room = room_repo.find_by_id(room_uuid)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Remove user from room
        room_repo.remove_participant(room_uuid, current_user_id)
        
        return {"message": "Left room successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get room details
    """
    try:
        room_uuid = UUID(room_id)
        current_user_id = current_user.id
        
        # Find room by ID
        room = room_repo.find_by_id(room_uuid)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Get topic repository for topic name lookup
        topic_repo = container.get_topic_repository()
        
        return RoomResponse(
            id=str(room.id),
            name=room.name,
            topic=get_topic_name(room.topic_id, topic_repo),
            participants=[str(p) for p in room.current_participants],
            max_participants=room.max_participants,
            status=room.status.name.lower(),
            created_at=room.created_at.isoformat(),
            livekit_room_name=room.livekit_room_name,
            livekit_token=room_repo.generate_livekit_token(room_uuid, current_user_id)
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

@router.get("/{room_id}/participants", response_model=List[ParticipantResponse])
async def get_room_participants(
    room_id: str,
    room_repo = Depends(get_room_repository),
    user_repo = Depends(get_user_repository)
):
    """
    Get room participants
    """
    try:
        room_uuid = UUID(room_id)
        
        # Find room by ID
        room = room_repo.find_by_id(room_uuid)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Get participant details
        participants = []
        for participant_id in room.current_participants:
            user = user_repo.find_by_id(participant_id)
            if user:
                participants.append(ParticipantResponse(
                    user_id=str(user.id),
                    display_name=user.display_name,
                    joined_at=room.created_at.isoformat(),  # Simplified - could track individual join times
                    is_speaking=False,  # Would need LiveKit integration for real-time status
                    connection_quality="good"  # Would need LiveKit integration for real status
                ))
        
        return participants
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

@router.get("/", response_model=RoomListResponse)
async def get_rooms(
    status: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get available rooms
    """
    try:
        current_user_id = current_user.id
        
        # Get rooms from repository
        if status == "active":
            rooms = room_repo.find_active_rooms(limit=limit)
        else:
            rooms = room_repo.find_active_rooms(limit=limit)  # Default to active rooms
        
        # Get topic repository for topic name lookup
        topic_repo = container.get_topic_repository()
        
        room_responses = []
        for room in rooms:
            room_responses.append(RoomResponse(
                id=str(room.id),
                name=room.name,
                topic=get_topic_name(room.topic_id, topic_repo),
                participants=[str(p) for p in room.current_participants],
                max_participants=room.max_participants,
                status=room.status.name.lower(),
                created_at=room.created_at.isoformat(),
                livekit_room_name=room.livekit_room_name,
                livekit_token=room_repo.generate_livekit_token(room.id, current_user_id)
            ))
        
        return RoomListResponse(
            rooms=room_responses,
            total=len(room_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 

# Additional dependency injection for AI features
def get_ai_host_service():
    return container.get_ai_host_service()

def get_openai_service():
    return container.get_openai_service()

def get_websocket_manager():
    """Dependency injection: Get singleton ConnectionManager"""
    return container.get_websocket_manager()


# NEW: GPT-4o Audio Real-time Room WebSocket
@router.websocket("/ws/{room_id}")
async def websocket_room_conversation(
    websocket: WebSocket,
    room_id: str,                    # Actual UUID
    livekit_name: str = Query(...),  # Retrieved from ?livekit_name=...
    user_id: str = Query(...)
):
    """
    WebSocket endpoint for GPT-4o Audio powered real-time room conversations
    
    Features:
    - 🎙️ Direct voice input/output using GPT-4o Audio
    - 🤖 Real-time AI moderator with voice responses  
    - 💬 Intelligent conversation guidance
    - 🔍 Live fact-checking and suggestions
    - 🎪 Automatic conversation flow management
    """
    await websocket.accept()
    logger.info(f"🎭 GPT-4o Audio room WebSocket connected: room={room_id}, livekit={livekit_name}, user={user_id}")
    
    try:
        # 1) First check entity
        room_repo = get_room_repository()
        room = room_repo.find_by_id(UUID(room_id))
        if not room:
            await websocket.send_json({"type":"error","message":"Room not found"})
            await websocket.close()
            return

        # 2) Connect to LiveKit with livekit_name
        room_participants = [str(uid) for uid in room.current_participants]
        websocket_manager = get_websocket_manager()
        room_connection_id = await websocket_manager.join_room(
            room_name=livekit_name,
            user_id=user_id,
            websocket=websocket
        )
        
        # 3) Send joined message
        await websocket.send_json({
            "type": "room_joined",
            "room_id": room_id,
            "connection_id": room_connection_id,
            "participants": room_participants,
            "ai_enabled": True,
            "supported_features": [
                "voice_input", "voice_output", "real_time_moderation", 
                "fact_checking", "conversation_guidance", "topic_suggestions"
            ]
        })

        # Initialize conversation context for AI moderator
        conversation_context = []
        openai_service = get_openai_service()
        
        # Main message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.info(f"📥 Received: {message_type} in room {room_id}")
            
            if message_type == "voice_message":
                # User sends voice message - process with GPT-4o Audio
                await handle_voice_message(
                    websocket, livekit_name, user_id, data, 
                    openai_service, conversation_context, room_participants
                )
                
            elif message_type == "text_message":
                # User sends text message
                await handle_text_message(
                    websocket, livekit_name, user_id, data,
                    openai_service, conversation_context, room_participants
                )
                
            elif message_type == "request_ai_assistance":
                # User explicitly requests AI help
                await handle_ai_assistance_request(
                    websocket, livekit_name, user_id, data,
                    openai_service, conversation_context, room_participants
                )
                
            elif message_type == "conversation_pause":
                # Handle conversation silence - AI suggests topics
                await handle_conversation_pause(
                    websocket, livekit_name, openai_service, 
                    conversation_context, room_participants
                )
                
            else:
                logger.warning(f"❓ Unknown message type: {message_type}")
                
    except WebSocketDisconnect:
        logger.info(f"👋 User {user_id} disconnected from room {room_id}")
        if 'room_connection_id' in locals():
            await websocket_manager.leave_room(livekit_name, room_connection_id)
        
    except Exception as e:
        logger.error(f"❌ Room WebSocket error: {e}")
        logger.exception("Full exception details:")
        await websocket.send_json({
            "type": "error",
            "error": str(e),
            "message": "Room connection error occurred"
        })


async def handle_voice_message(
    websocket: WebSocket, 
    room_id: str, 
    user_id: str, 
    data: dict,
    openai_service,
    conversation_context: list,
    room_participants: list
):
    """
    Process user voice messages - Use GPT-4o Audio for real-time response
    """
    try:
        audio_data = data.get("audio_data")  # base64 encoded audio
        if not audio_data:
            await websocket.send_json({
                "type": "error", 
                "message": "No audio data provided"
            })
            return
            
        logger.info(f"🎙️ Processing voice message from {user_id} with GPT-4o Audio...")
        
        # Add user message to context
        user_context = {
            "role": "user",
            "content": f"[{user_id} sent a voice message]",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "voice"
        }
        conversation_context.append(user_context)
        
        # Use GPT-4o Audio to process and respond
        ai_response = await openai_service.moderate_room_conversation(
            audio_data=audio_data,
            conversation_context=conversation_context,
            room_participants=room_participants,
            moderation_mode="active_host"
        )
        
        # Broadcast user's voice message to other participants
        await broadcast_to_room(room_id, {
            "type": "user_voice_message",
            "user_id": user_id,
            "audio_data": audio_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send AI moderator response
        if ai_response.get("ai_response"):
            ai_reply = ai_response["ai_response"]
            
            # Add AI response to context
            ai_context = {
                "role": "assistant",
                "content": ai_reply.get("text", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ai_moderation"
            }
            conversation_context.append(ai_context)
            
            # Broadcast AI voice response to all participants
            await broadcast_to_room(room_id, {
                "type": "ai_moderator_response",
                "response_text": ai_reply.get("text"),
                "response_audio": ai_reply.get("audio"),  # base64 audio
                "audio_transcript": ai_reply.get("audio_transcript"),
                "suggestions": ai_response.get("suggestions", []),
                "moderation_type": ai_response.get("moderation_type"),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        logger.info("✅ Voice message processed and AI response sent")
        
    except Exception as e:
        logger.error(f"❌ Voice message handling failed: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to process voice message: {str(e)}"
        })


async def handle_text_message(
    websocket: WebSocket,
    room_id: str, 
    user_id: str,
    data: dict,
    openai_service,
    conversation_context: list,
    room_participants: list
):
    """
    Handle user text messages - AI provides intelligent replies and suggestions
    """
    try:
        text_content = data.get("text", "")
        if not text_content.strip():
            return
            
        logger.info(f"💬 Processing text message from {user_id}: '{text_content[:50]}...'")
        
        # Add to context
        conversation_context.append({
            "role": "user", 
            "content": text_content,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "text"
        })
        
        # Broadcast user message
        await broadcast_to_room(room_id, {
            "type": "user_text_message",
            "user_id": user_id,
            "text": text_content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Get AI moderator response (text + optional voice)
        ai_response = await openai_service.moderate_room_conversation(
            text_input=text_content,
            conversation_context=conversation_context,
            room_participants=room_participants,
            moderation_mode="secretary"  # More subtle for text
        )
        
        # Send AI response if meaningful
        if ai_response.get("ai_response") and ai_response["ai_response"].get("text"):
            ai_reply = ai_response["ai_response"]
            
            conversation_context.append({
                "role": "assistant",
                "content": ai_reply.get("text"),
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ai_suggestion"
            })
            
            await broadcast_to_room(room_id, {
                "type": "ai_suggestion",
                "suggestion_text": ai_reply.get("text"),
                "suggestion_audio": ai_reply.get("audio"),
                "suggestions": ai_response.get("suggestions", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ Text message handling failed: {e}")


async def handle_ai_assistance_request(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    data: dict,
    openai_service,
    conversation_context: list,
    room_participants: list
):
    """
    Handle user request for AI assistance
    """
    try:
        request_type = data.get("assistance_type", "general")  # general, fact_check, topic_suggestion
        
        logger.info(f"🆘 AI assistance requested by {user_id}: {request_type}")
        
        ai_response = await openai_service.moderate_room_conversation(
            text_input=f"User requested AI assistance, type: {request_type}",
            conversation_context=conversation_context,
            room_participants=room_participants,
            moderation_mode="fact_checker" if request_type == "fact_check" else "active_host"
        )
        
        if ai_response.get("ai_response"):
            ai_reply = ai_response["ai_response"]
            
            await broadcast_to_room(room_id, {
                "type": "ai_assistance_response",
                "requested_by": user_id,
                "assistance_type": request_type,
                "response_text": ai_reply.get("text"),
                "response_audio": ai_reply.get("audio"),
                "suggestions": ai_response.get("suggestions", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ AI assistance handling failed: {e}")


async def handle_conversation_pause(
    websocket: WebSocket,
    room_id: str,
    openai_service,
    conversation_context: list,
    room_participants: list
):
    """
    Handle conversation pause - AI suggests topics to keep conversation active
    """
    try:
        logger.info(f"⏸️ Conversation pause detected in room {room_id}")
        
        ai_response = await openai_service.moderate_room_conversation(
            text_input="Conversation has paused, providing topic suggestions to keep it lively",
            conversation_context=conversation_context,
            room_participants=room_participants,
            moderation_mode="active_host"
        )
        
        if ai_response.get("ai_response"):
            ai_reply = ai_response["ai_response"]
            
            await broadcast_to_room(room_id, {
                "type": "conversation_revival",
                "topic_suggestion": ai_reply.get("text"),
                "suggestion_audio": ai_reply.get("audio"),
                "suggestions": ai_response.get("suggestions", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ Conversation pause handling failed: {e}")


async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to all room participants"""
    try:
        manager = get_websocket_manager()
        await manager.broadcast_to_room(room_id, message)
    except Exception as e:
        logger.error(f"❌ Room broadcast failed: {e}")
