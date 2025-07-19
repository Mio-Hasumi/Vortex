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
@router.post("/request", response_model=MatchResponse)
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

@router.delete("/request")
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

@router.get("/queue/status", response_model=QueueStatusResponse)
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
                "message": "user_id query parameter required (e.g., ws://localhost:8000/api/matching/ws?user_id=your-uuid)"
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
                "message": "user_id query parameter required (e.g., ws://localhost:8000/api/matching/ws/general?user_id=your-uuid)"
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