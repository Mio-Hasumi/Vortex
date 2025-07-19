"""
Matching API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import asyncio
import json
import logging
from datetime import datetime
import os

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import MatchStatus, User

logger = logging.getLogger(__name__)

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

# Dependency injection
def get_matching_repository():
    return container.get_matching_repository()

def get_topic_repository():
    return container.get_topic_repository()

def get_websocket_manager():
    return container.get_websocket_manager()

def get_event_broadcaster():
    return container.get_event_broadcaster()

# NEW: AI service dependencies
def get_ai_host_service():
    return container.get_ai_host_service()

def get_openai_service():
    return container.get_openai_service()

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
        from infrastructure.repositories.matching_repository import new_match
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
            language_preference=request.language_preference
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
        
        # Step 2: Based on hashtags, perform intelligent matching
        match_candidates = await matching_repo.find_users_by_hashtags(
            hashtags=generated_hashtags,
            exclude_user_id=current_user_id,
            max_results=10,
            min_similarity=0.2  # At least 20% similarity
        )
        
        # Step 3: Select the best match
        if match_candidates:
            # Sort by similarity and select the best match
            best_match = max(match_candidates, key=lambda x: x.get("similarity", 0))
            matched_user_id = best_match["user_id"]
            match_confidence = best_match["similarity"]
            
            logger.info(f"🎯 Found match: {matched_user_id} (confidence: {match_confidence:.2f})")
            
            # Create an AI hosted room session
            ai_session_id = f"ai_session_{current_user_id}_{matched_user_id}_{datetime.utcnow().timestamp()}"
            
            # Add users to the matching queue (if room management is needed)
            await matching_repo.create_ai_match(
                user1_id=current_user_id,
                user2_id=matched_user_id,
                hashtags=generated_hashtags,
                confidence=match_confidence,
                ai_session_id=ai_session_id
            )
            
            estimated_wait_time = 5  # Almost instant match
            status_msg = "matched"
            
        else:
            # No match found, add to waiting queue
            logger.info("🔍 No immediate match found, adding to queue...")
            
            ai_session_id = f"ai_waiting_{current_user_id}_{datetime.utcnow().timestamp()}"
            
            await matching_repo.add_to_ai_queue(
                user_id=current_user_id,
                hashtags=generated_hashtags,
                voice_input=understood_text,
                ai_session_id=ai_session_id
            )
            
            estimated_wait_time = 30  # Estimated wait time
            status_msg = "waiting_for_match"
        
        # Step 4: Generate a unique match ID
        match_id = f"ai_match_{current_user_id}_{datetime.utcnow().timestamp()}"
        
        # Build the response
        response = AIMatchResponse(
            match_id=match_id,
            session_id=ai_session_id,
            extracted_topics=extracted_topics,
            generated_hashtags=generated_hashtags,
            match_confidence=match_confidence if match_candidates else 0.0,
            estimated_wait_time=estimated_wait_time,
            ai_greeting=voice_processing_result.get("text_response", ""),
            status=status_msg
        )
        
        # Step 5: Broadcast match event (if real-time matching)
        if match_candidates:
            await event_broadcaster.broadcast_ai_match_found(
                user1_id=current_user_id,
                user2_id=matched_user_id,
                match_data={
                    "match_id": match_id,
                    "session_id": ai_session_id,
                    "hashtags": generated_hashtags,
                    "confidence": match_confidence,
                    "ai_audio_response": voice_processing_result.get("audio_response")
                }
            )
        
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
        
        if not user_id_param:
            # Accept connection to send error message
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"user_id query parameter required (e.g., ws://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost:8000')}/api/matching/ws?user_id=your-uuid)"
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
        
        # Register connection with WebSocket manager (this will accept the connection)
        connection_id = await websocket_manager.connect(websocket, user_id, "matching")
        
        # Keep connection alive and handle messages
        async for message in websocket.iter_text():
            try:
                msg_data = json.loads(message)
                
                if msg_data.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {message}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                break
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for matching")
    except Exception as e:
        logger.error(f"❌ Error in WebSocket endpoint: {e}")
    finally:
        # Cleanup is handled by the connection manager
        pass

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