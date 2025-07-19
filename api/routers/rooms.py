"""
Rooms API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import RoomStatus, User, Room
from uuid import uuid4

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
@router.post("/create", response_model=RoomResponse)
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