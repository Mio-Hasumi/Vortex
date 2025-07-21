"""
Matching API endpoints for the VoiceApp backend
Handles voice-based matching, topic-based matching, and real-time match updates via WebSocket
"""

import json
import os
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import MatchStatus, User

logger = logging.getLogger(__name__)

# Dependency injection functions
def get_websocket_manager():
    """Get WebSocket manager instance"""
    return container.get_websocket_manager()

def get_matching_repository():
    """Get matching repository instance"""
    return container.get_matching_repository()

def get_ai_host_service():
    """Get AI host service instance"""
    return container.get_ai_host_service()

def get_openai_service():
    """Get OpenAI service instance"""
    return container.get_openai_service()

def get_room_repository():
    """Get room repository instance"""
    return container.get_room_repository()

def get_topic_repository():
    """Get topic repository instance"""
    return container.get_topic_repository()

def get_event_broadcaster():
    """Get event broadcaster instance"""
    return container.get_event_broadcaster()

router = APIRouter()

# Request/Response Models
class MatchRequest(BaseModel):
    preferred_topics: List[str]
    max_participants: int = 3
    language_preference: Optional[str] = None

# NEW: AI-driven matching models
class AIMatchRequest(BaseModel):
    user_voice_input: str  # User's voice input text
    audio_file_url: Optional[str] = None  # Optional audio file URL
    max_participants: int = 2
    language_preference: Optional[str] = "en-US"

class AIMatchResponse(BaseModel):
    match_id: str
    session_id: str  # AI host session ID
    extracted_topics: List[str]
    generated_hashtags: List[str]
    match_confidence: float
    estimated_wait_time: int
    ai_greeting: str
    status: str

class MatchResponse(BaseModel):
    match_id: str
    room_id: str
    participants: List[str]
    topic: str
    status: str
    estimated_wait_time: int

class QueueStatusResponse(BaseModel):
    position: int
    estimated_wait_time: int
    queue_size: int

# NEW: Match confirmation response model
class MatchConfirmationResponse(BaseModel):
    match_id: str
    status: str
    is_ready: bool
    room_id: Optional[str] = None
    room_name: Optional[str] = None
    livekit_room_name: Optional[str] = None
    livekit_token: Optional[str] = None
    topic: Optional[str] = None
    participants: Optional[List[dict]] = None
    match_confidence: Optional[float] = None
    created_at: Optional[str] = None
    matched_at: Optional[str] = None
    message: Optional[str] = None
    estimated_wait_time: Optional[int] = None

# Helper functions
def get_topic_name_for_match(match, topic_repo) -> str:
    """Get topic name for a match, fallback to 'General' if not found"""
    try:
        # Try to get topic from the first preferred topic if available
        # This is simplified - in production you might store the actual matched topic
        if hasattr(match, 'preferred_topics') and match.preferred_topics:
            topic_id = UUID(match.preferred_topics[0])
            topic = topic_repo.find_by_id(topic_id)
            return topic.name if topic else "General"
        return "General"
    except:
        return "General"

# Matching endpoints
@router.post("/match", response_model=MatchResponse)
async def request_match(
    request: MatchRequest,
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Request to be matched with other users
    """
    try:
        current_user_id = current_user.id
        
        # Create a match record
        from domain.entities import new_match
        match = new_match(
            user_id=current_user_id,
            preferred_topics=request.preferred_topics,
            max_participants=request.max_participants
        )
        
        # Add user to matching queue
        queue_preferences = {
            "preferred_topics": request.preferred_topics,
            "max_participants": request.max_participants,
            "language_preference": request.language_preference
        }
        matching_repo.add_to_queue(current_user_id, queue_preferences)
        
        # Save match to repository
        saved_match = matching_repo.save_match(match)
        
        return MatchResponse(
            match_id=str(saved_match.id),
            room_id=str(saved_match.room_id) if saved_match.room_id else "",
            participants=[str(saved_match.user_id)] + [str(u) for u in saved_match.matched_users],
            topic=request.preferred_topics[0] if request.preferred_topics else "General",
            status=saved_match.status.name.lower(),
            estimated_wait_time=30  # Mock estimate
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/cancel")
async def cancel_match(
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel pending match request
    """
    try:
        current_user_id = current_user.id
        
        # Remove user from matching queue
        matching_repo.remove_from_queue(current_user_id)
        
        return {"message": "Match request cancelled"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get current position in matching queue
    """
    try:
        current_user_id = current_user.id
        
        # Get queue information from repository
        position = matching_repo.get_queue_position(current_user_id)
        queue_size = matching_repo.get_queue_size()
        
        return QueueStatusResponse(
            position=position,
            estimated_wait_time=position * 30,  # Mock estimate: 30 seconds per position
            queue_size=queue_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history")
async def get_match_history(
    limit: int = 20, 
    offset: int = 0,
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's match history
    """
    try:
        current_user_id = current_user.id
        
        # Get matches from repository
        matches = matching_repo.find_matches_by_user_id(current_user_id, limit=limit)
        
        # Get topic repository for name lookup
        topic_repo = container.get_topic_repository()
        
        match_history = []
        for match in matches:
            match_history.append({
                "match_id": str(match.id),
                "topic": get_topic_name_for_match(match, topic_repo),
                "participants": [str(match.user_id)] + [str(u) for u in match.matched_users],
                "created_at": match.created_at.isoformat(),
                "status": match.status.name.lower()
            })
        
        return {
            "matches": match_history,
            "total": len(match_history)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/process-timeout-matches")
async def process_timeout_matches_manually(
    timeout_minutes: float = 1.0,
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger timeout matching process (for testing/admin use)
    """
    try:
        # Check current timeout users count
        timeout_users_count = matching_repo.get_timeout_users_count(timeout_minutes)
        
        if timeout_users_count < 2:
            return {
                "message": f"Only {timeout_users_count} users waiting over {timeout_minutes} minute(s). Need at least 2 users for matching.",
                "timeout_users_count": timeout_users_count,
                "matches_created": []
            }
        
        # Process timeout matches
        matches_created = matching_repo.process_timeout_matches(timeout_minutes)
        
        return {
            "message": f"Processed timeout matching for {timeout_users_count} users waiting over {timeout_minutes} minute(s)",
            "timeout_users_count": timeout_users_count,
            "matches_created": len(matches_created),
            "matches": matches_created
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process timeout matches: {str(e)}"
        )

@router.get("/timeout-stats") 
async def get_timeout_stats(
    timeout_minutes: float = 1.0,
    matching_repo = Depends(get_matching_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about users waiting too long
    """
    try:
        timeout_users_count = matching_repo.get_timeout_users_count(timeout_minutes)
        total_queue_size = matching_repo.get_queue_size()
        
        return {
            "total_queue_size": total_queue_size,
            "timeout_users_count": timeout_users_count,
            "timeout_minutes": timeout_minutes,
            "timeout_percentage": (timeout_users_count / total_queue_size * 100) if total_queue_size > 0 else 0,
            "ready_for_timeout_matching": timeout_users_count >= 2
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# NEW: AI-Driven Matching Endpoint with GPT-4o Audio
@router.post("/ai-match", response_model=AIMatchResponse)
async def ai_driven_match(
    request: AIMatchRequest,
    matching_repo = Depends(get_matching_repository),
    ai_host_service = Depends(get_ai_host_service),
    openai_service = Depends(get_openai_service),
    current_user: User = Depends(get_current_user)
):
    """
    NEW: Simplified AI-driven matching using GPT-4o Audio Preview
    
    User registers and directly inputs voice → GPT-4o processes → Intelligent matching
    
    Workflow:
    1. User voice input: "I want to talk about AI and entrepreneurship"
    2. GPT-4o Audio directly understands and extracts hashtags
    3. Match users based on hashtag similarity
    4. Return match results and AI voice confirmation
    """
    try:
        current_user_id = current_user.id
        
        logger.info(f"🎯 Starting simplified AI-driven match for user: {current_user_id}")
        logger.info(f"🎙️ Processing voice input with GPT-4o Audio...")
        
        # Step 1: Use GPT-4o Audio to directly process user voice input
        # This step replaces the previous STT → GPT → hashtag multi-step process
        voice_processing_result = await openai_service.process_voice_input_for_matching(
            audio_data=request.user_voice_input,  # Can be base64 or audio URL
            language=request.language_preference
        )
        
        if voice_processing_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Voice processing failed: {voice_processing_result['error']}"
            )
        
        extracted_topics = voice_processing_result.get("extracted_topics", [])
        generated_hashtags = voice_processing_result.get("generated_hashtags", [])
        understood_text = voice_processing_result.get("understood_text", "")
        
        logger.info(f"✅ Voice processed successfully:")
        logger.info(f"   📝 Understood: {understood_text}")
        logger.info(f"   🏷️ Topics: {extracted_topics}")
        logger.info(f"   #️⃣ Hashtags: {generated_hashtags}")
        
        # Step 2: Always add user to queue first (let background matcher handle matching)
        logger.info("🔍 Adding user to AI matching queue...")
        
        ai_session_id = f"ai_waiting_{str(current_user_id)}_{datetime.utcnow().timestamp()}"
        
        matching_repo.add_to_ai_queue(
            user_id=str(current_user_id),
            hashtags=generated_hashtags,
            voice_input=understood_text,
            ai_session_id=ai_session_id
        )
        
        # Always return waiting status - let background matcher create matches when both users have WebSocket connections
        estimated_wait_time = 15  # Expected wait time for background matching
        status_msg = "waiting_for_match"
        match_confidence = 0.0  # Will be determined by background matcher
        
        # Step 4: Generate a unique match ID
        match_id = f"ai_match_{str(current_user_id)}_{datetime.utcnow().timestamp()}"
        
        # Build the response - always waiting status
        response = AIMatchResponse(
            match_id=match_id,
            session_id=ai_session_id,
            extracted_topics=extracted_topics,
            generated_hashtags=generated_hashtags,
            match_confidence=match_confidence,
            estimated_wait_time=estimated_wait_time,
            ai_greeting=voice_processing_result.get("text_response", ""),
            status=status_msg
        )
        
        # No immediate matching - let background queue monitor handle this when both users have WebSocket connections
        
        logger.info(f"🎉 AI-driven match process completed successfully!")
        logger.info(f"   📊 Status: {status_msg}")
        logger.info(f"   ⏱️ Wait time: {estimated_wait_time}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ AI-driven matching failed: {e}")
        logger.exception("Full exception details:")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI matching service error: {str(e)}"
        )

@router.get("/confirm/{match_id}", response_model=MatchConfirmationResponse)
async def confirm_match(
    match_id: str,
    matching_repo = Depends(get_matching_repository),
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm a match and get room details for joining
    
    This endpoint allows the frontend to:
    1. Confirm that a match was successful
    2. Get room details (room_id, livekit_token, etc.)
    3. Get participant information
    4. Navigate to the conversation room
    """
    try:
        current_user_id = current_user.id
        
        logger.info(f"🔍 Confirming match {match_id} for user {current_user_id}")
        
        # Find the match record
        match = matching_repo.find_match_by_id(match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match {match_id} not found"
            )
        
        # Verify the user is part of this match
        if match.user_id != current_user_id and current_user_id not in match.matched_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not part of this match"
            )
        
        # Check match status
        if match.status.name.lower() != "matched":
            return MatchConfirmationResponse(
                match_id=match_id,
                status=match.status.name.lower(),
                is_ready=False,
                message=f"Match is not ready yet. Current status: {match.status.name.lower()}",
                estimated_wait_time=match.estimated_wait_time if hasattr(match, 'estimated_wait_time') else 30
            )
        
        # Get room details if match is successful
        if match.room_id:
            room = room_repo.find_by_id(match.room_id)
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Matched room not found"
                )
            
            # Generate LiveKit token for the user
            livekit_token = room_repo.generate_livekit_token(match.room_id, current_user_id)
            
            # Get participant details
            user_repo = container.get_user_repository()
            participants = []
            all_participant_ids = [match.user_id] + match.matched_users
            
            for participant_id in all_participant_ids:
                user = user_repo.find_by_id(participant_id)
                if user:
                    participants.append({
                        "user_id": str(participant_id),
                        "display_name": user.display_name,
                        "is_current_user": participant_id == current_user_id
                    })
            
            # Get topic information
            topic_repo = container.get_topic_repository()
            topic_name = "General Chat"
            if match.selected_topic_id:
                topic = topic_repo.find_by_id(match.selected_topic_id)
                if topic:
                    topic_name = topic.name
            
            logger.info(f"✅ Match confirmed successfully: {match_id}")
            
            return MatchConfirmationResponse(
                match_id=match_id,
                status="matched",
                is_ready=True,
                room_id=str(match.room_id),
                room_name=room.name,
                livekit_room_name=room.livekit_room_name,
                livekit_token=livekit_token,
                topic=topic_name,
                participants=participants,
                match_confidence=getattr(match, 'confidence', 1.0),
                created_at=match.created_at.isoformat(),
                matched_at=match.matched_at.isoformat() if match.matched_at else None,
                message="Match confirmed! Ready to join conversation."
            )
        else:
            # Match exists but no room yet (shouldn't happen)
            logger.warning(f"⚠️ Match {match_id} has no room_id")
            return MatchConfirmationResponse(
                match_id=match_id,
                status="matched",
                is_ready=False,
                message="Match found but room is being prepared. Please try again in a moment.",
                estimated_wait_time=10
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to confirm match {match_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm match: {str(e)}"
        )

# WebSocket endpoint for real-time matching updates
@router.websocket("/ws")
async def websocket_matching(websocket: WebSocket):
    """
    WebSocket endpoint for real-time matching updates
    """
    websocket_manager = get_websocket_manager()
    
    try:
        # Get user_id from query parameters if available
        user_id_param = websocket.query_params.get("user_id")
        
        logger.info(f"🔌🔌🔌 [MATCHING_WS] ===== NEW CONNECTION ATTEMPT =====")
        logger.info(f"🔌 [MATCHING_WS] Query params: {dict(websocket.query_params)}")
        logger.info(f"🔌 [MATCHING_WS] User ID param: {user_id_param}")
        logger.info(f"🔌 [MATCHING_WS] Headers: {dict(websocket.headers)}")
        
        if not user_id_param:
            logger.error(f"❌ [MATCHING_WS] Missing user_id parameter!")
            # Accept connection to send error message
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"user_id query parameter required (e.g., ws://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost:8000')}/api/matching/ws?user_id=your-uuid)"
            }))
            await websocket.close(code=1008)
            logger.error(f"❌ [MATCHING_WS] Connection closed due to missing user_id")
            return
        
        try:
            user_id = UUID(user_id_param)
            logger.info(f"✅ [MATCHING_WS] Valid user UUID: {user_id}")
        except ValueError:
            logger.error(f"❌ [MATCHING_WS] Invalid UUID format: {user_id_param}")
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid user_id format. Must be a valid UUID"
            }))
            await websocket.close(code=1008)
            logger.error(f"❌ [MATCHING_WS] Connection closed due to invalid UUID")
            return
        
        logger.info(f"🔌 [MATCHING_WS] About to register connection for user: {user_id}")
        
        # Register connection with WebSocket manager (this will accept the connection)
        connection_id = await websocket_manager.connect(websocket, user_id, "matching")
        
        logger.info(f"✅✅✅ [MATCHING_WS] Connection registered successfully!")
        logger.info(f"   🆔 Connection ID: {connection_id}")
        logger.info(f"   👤 User ID: {user_id}")
        logger.info(f"   🔗 Connection type: matching")
        
        # Send welcome message immediately
        welcome_message = {
            "type": "welcome",
            "message": "Connected to matching service",
            "user_id": str(user_id),
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        logger.info(f"👋 [MATCHING_WS] Welcome message sent to {user_id}")
        
        # Main message handling loop
        logger.info(f"🔄 [MATCHING_WS] Starting message handling loop...")
        
        try:
            async for message in websocket.iter_text():
                try:
                    logger.debug(f"📥 [MATCHING_WS] Received message from {user_id}: {message}")
                    
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    logger.debug(f"📋 [MATCHING_WS] Processing message type: {message_type}")
                    
                    if message_type == "ping":
                        # Heartbeat
                        pong_message = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(pong_message))
                        logger.debug(f"💓 [MATCHING_WS] Sent pong to {user_id}")
                    
                    elif message_type == "auth":
                        # Authentication (if needed)
                        auth_response = {
                            "type": "authenticated",
                            "user_id": str(user_id),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(auth_response))
                        logger.info(f"🔐 [MATCHING_WS] Authentication confirmed for {user_id}")
                    
                    else:
                        logger.warning(f"❓ [MATCHING_WS] Unknown message type: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ [MATCHING_WS] Invalid JSON from {user_id}: {message}")
                except Exception as e:
                    logger.error(f"❌ [MATCHING_WS] Error processing message from {user_id}: {e}")
                    
        except WebSocketDisconnect:
            logger.info(f"👋👋👋 [MATCHING_WS] WebSocket disconnect (normal): {user_id}")
        except Exception as e:
            logger.error(f"❌ [MATCHING_WS] Unexpected error in message loop: {e}")
            logger.exception("Full exception details:")
        
    except Exception as e:
        logger.error(f"❌❌❌ [MATCHING_WS] Fatal error in WebSocket handler: {e}")
        logger.exception("Full exception details:")
        
    finally:
        # Cleanup
        if 'connection_id' in locals():
            logger.info(f"🧹 [MATCHING_WS] Cleaning up connection: {connection_id}")
            await websocket_manager.disconnect(connection_id)
        else:
            logger.warning(f"⚠️ [MATCHING_WS] No connection_id to cleanup")
            
        logger.info(f"🔌🔌🔌 [MATCHING_WS] ===== CONNECTION CLOSED =====")
        logger.info(f"🔌 [MATCHING_WS] User: {user_id_param if 'user_id_param' in locals() else 'unknown'}")
        logger.info(f"🔌 [MATCHING_WS] Connection duration: [WebSocket closed]")

# General WebSocket endpoint
@router.websocket("/ws/general")  
async def websocket_general(websocket: WebSocket):
    """
    General WebSocket endpoint for notifications
    """
    websocket_manager = get_websocket_manager()
    
    try:
        # Get user_id from query parameters
        user_id_param = websocket.query_params.get("user_id")
        
        if not user_id_param:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"user_id query parameter required (e.g., ws://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost:8000')}/api/matching/ws/general?user_id=your-uuid)"
            }))
            await websocket.close(code=1008)
            return
        
        try:
            user_id = UUID(user_id_param)
        except ValueError:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid user_id format. Must be a valid UUID"
            }))
            await websocket.close(code=1008)
            return
        
        # Register connection (this will accept the connection)
        connection_id = await websocket_manager.connect(websocket, user_id, "general")
        
        # Keep connection alive
        async for message in websocket.iter_text():
            try:
                msg_data = json.loads(message)
                
                if msg_data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong", 
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {message}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for general")
    except Exception as e:
        logger.error(f"❌ Error in general WebSocket: {e}") 