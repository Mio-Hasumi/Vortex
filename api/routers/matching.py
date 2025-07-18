"""
Matching API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import asyncio
import json

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import MatchStatus, User

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
        
        match_history = []
        for match in matches:
            match_history.append({
                "match_id": str(match.id),
                "topic": "General",  # TODO: Get topic name from preferred_topics
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
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time matching updates
    """
    await websocket.accept()
    
    try:
        while True:
            # TODO: Implement real-time matching updates
            # 1. Listen for queue position changes
            # 2. Send match found notifications
            # 3. Handle connection management
            
            # For now, send periodic updates
            await asyncio.sleep(5)
            await websocket.send_text(json.dumps({
                "type": "queue_update",
                "position": 3,
                "estimated_wait_time": 90
            }))
            
    except WebSocketDisconnect:
        # TODO: Clean up user from matching queue
        # matching_repo.remove_from_queue(current_user_id)
        pass
    except Exception as e:
        await websocket.close(code=1000) 