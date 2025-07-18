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
async def join_room(request: JoinRoomRequest):
    """
    Join an existing room
    """
    try:
        # TODO: Implement room joining
        # 1. Check room availability
        # 2. Add user to room
        # 3. Generate LiveKit token
        
        return RoomResponse(
            id=request.room_id,
            name="Tech Discussion",
            topic="Technology",
            participants=["user-1", "user-2"],
            max_participants=10,
            status="active",
            created_at="2023-12-01T10:00:00Z",
            livekit_room_name=request.room_id,
            livekit_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{room_id}/leave")
async def leave_room(room_id: str):
    """
    Leave a room
    """
    try:
        # TODO: Implement room leaving
        # 1. Remove user from room
        # 2. Update room status if needed
        # 3. Notify other participants
        
        return {"message": "Left room successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str):
    """
    Get room details
    """
    try:
        # TODO: Implement room retrieval
        return RoomResponse(
            id=room_id,
            name="Tech Discussion",
            topic="Technology",
            participants=["user-1", "user-2"],
            max_participants=10,
            status="active",
            created_at="2023-12-01T10:00:00Z",
            livekit_room_name=room_id,
            livekit_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

@router.get("/{room_id}/participants", response_model=List[ParticipantResponse])
async def get_room_participants(room_id: str):
    """
    Get room participants
    """
    try:
        # TODO: Implement participant retrieval
        return [
            ParticipantResponse(
                user_id="user-1",
                display_name="Alice",
                joined_at="2023-12-01T10:00:00Z",
                is_speaking=True,
                connection_quality="excellent"
            ),
            ParticipantResponse(
                user_id="user-2",
                display_name="Bob",
                joined_at="2023-12-01T10:02:00Z",
                is_speaking=False,
                connection_quality="good"
            )
        ]
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
    room_repo = Depends(get_room_repository)
):
    """
    Get available rooms
    """
    try:
        # Get rooms from repository
        if status == "active":
            rooms = room_repo.find_active_rooms(limit=limit)
        else:
            rooms = room_repo.find_active_rooms(limit=limit)  # Default to active rooms
        
        room_responses = []
        for room in rooms:
            room_responses.append(RoomResponse(
                id=str(room.id),
                name=room.name,
                topic="General",  # TODO: Get topic name from topic_id
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