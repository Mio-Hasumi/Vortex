"""
Friends API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import FriendshipStatus, User
from infrastructure.repositories.friend_repository import new_friendship

router = APIRouter()

# Request/Response Models
class FriendResponse(BaseModel):
    user_id: str
    display_name: str
    status: str  # online, offline, in_call
    last_seen: Optional[str]
    friendship_status: str  # pending, accepted, blocked

class FriendRequestResponse(BaseModel):
    id: str
    from_user_id: str
    from_display_name: str
    to_user_id: str
    to_display_name: str
    status: str  # pending, accepted, rejected
    created_at: str

class SendFriendRequestRequest(BaseModel):
    user_id: str
    message: Optional[str] = None

class FriendListResponse(BaseModel):
    friends: List[FriendResponse]
    total: int

class FriendRequestListResponse(BaseModel):
    requests: List[FriendRequestResponse]
    total: int

# Dependency injection
def get_friend_repository():
    return container.get_friend_repository()

def get_user_repository():
    return container.get_user_repository()

# Friends endpoints
@router.get("/", response_model=FriendListResponse)
async def get_friends(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    friend_repo = Depends(get_friend_repository),
    user_repo = Depends(get_user_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's friends list
    """
    try:
        current_user_id = current_user.id
        
        # Get friendships from repository
        friendships = friend_repo.find_friendships_by_user_id(current_user_id)
        
        friend_responses = []
        for friendship in friendships:
            # Get friend's user info
            friend_user = user_repo.find_by_id(friendship.friend_id)
            if friend_user:
                friend_responses.append(FriendResponse(
                    user_id=str(friendship.friend_id),
                    display_name=friend_user.display_name,
                    status="online",  # TODO: Get real status
                    last_seen=friendship.created_at.isoformat(),
                    friendship_status=friendship.status.name.lower()
                ))
        
        return FriendListResponse(
            friends=friend_responses,
            total=len(friend_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/request")
async def send_friend_request(
    request: SendFriendRequestRequest,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Send a friend request
    """
    try:
        current_user_id = current_user.id
        
        # Create friendship request
        friendship = new_friendship(
            user_id=current_user_id,
            friend_id=UUID(request.user_id),
            message=request.message
        )
        
        # Save to repository
        saved_friendship = friend_repo.save_friendship(friendship)
        
        return {"message": "Friend request sent successfully", "request_id": str(saved_friendship.id)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/requests", response_model=FriendRequestListResponse)
async def get_friend_requests(
    type: str = "received",  # received, sent
    limit: int = 20,
    offset: int = 0
):
    """
    Get friend requests (received or sent)
    """
    try:
        # TODO: Implement friend request retrieval
        return FriendRequestListResponse(
            requests=[
                FriendRequestResponse(
                    id="req-123",
                    from_user_id="user-4",
                    from_display_name="Charlie",
                    to_user_id="user-1",
                    to_display_name="Current User",
                    status="pending",
                    created_at="2023-12-01T09:00:00Z"
                )
            ],
            total=1
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/requests/{request_id}/accept")
async def accept_friend_request(
    request_id: str,
    friend_repo = Depends(get_friend_repository)
):
    """
    Accept a friend request
    """
    try:
        request_uuid = UUID(request_id)
        
        # Get the friendship request
        friendship_request = friend_repo.find_friendship_by_id(request_uuid)
        if not friendship_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )
        
        # Update request status to accepted
        friend_repo.update_friendship_status(request_uuid, FriendshipStatus.ACCEPTED)
        
        # Create reverse friendship relationship
        reverse_friendship = new_friendship(
            user_id=friendship_request.friend_id,
            friend_id=friendship_request.user_id
        )
        reverse_friendship.status = FriendshipStatus.ACCEPTED
        
        # Save reverse friendship
        friend_repo.save_friendship(reverse_friendship)
        
        return {"message": "Friend request accepted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/requests/{request_id}/reject")
async def reject_friend_request(request_id: str):
    """
    Reject a friend request
    """
    try:
        # TODO: Implement friend request rejection
        return {"message": "Friend request rejected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{user_id}")
async def remove_friend(user_id: str):
    """
    Remove a friend
    """
    try:
        # TODO: Implement friend removal
        # 1. Remove friendship
        # 2. Send notification
        
        return {"message": "Friend removed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/block")
async def block_user(user_id: str):
    """
    Block a user
    """
    try:
        # TODO: Implement user blocking
        # 1. Add to blocked users list
        # 2. Remove from friends if applicable
        
        return {"message": "User blocked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{user_id}/block")
async def unblock_user(user_id: str):
    """
    Unblock a user
    """
    try:
        # TODO: Implement user unblocking
        return {"message": "User unblocked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 