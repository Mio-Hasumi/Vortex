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
    message: Optional[str] = None

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

def get_redis_service():
    return container.get_redis_service()

# Friends endpoints
@router.get("/", response_model=FriendListResponse)
async def get_friends(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    friend_repo = Depends(get_friend_repository),
    user_repo = Depends(get_user_repository),
    redis_service = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's friends list with real-time online status
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
                # Get real online status from Redis
                is_online = redis_service.is_user_online(friendship.friend_id)
                status = "online" if is_online else "offline"
                
                friend_responses.append(FriendResponse(
                    user_id=str(friendship.friend_id),
                    display_name=friend_user.display_name,
                    status=status,
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
    offset: int = 0,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get friend requests (received or sent)
    """
    try:
        current_user_id = current_user.id
        
        # Get pending requests from repository
        pending_requests = friend_repo.find_pending_requests_by_user_id(current_user_id)
        
        request_responses = []
        for friendship in pending_requests:
            # Determine if this is a received or sent request
            is_received = (friendship.friend_id == current_user_id)
            
            if (type == "received" and is_received) or (type == "sent" and not is_received):
                request_responses.append(FriendRequestResponse(
                    id=str(friendship.id),
                    from_user_id=str(friendship.user_id),
                    from_display_name="User",  # Could be enhanced with user lookup
                    to_user_id=str(friendship.friend_id), 
                    to_display_name="Friend",  # Could be enhanced with user lookup
                    status=friendship.status.name.lower(),
                    created_at=friendship.created_at.isoformat(),
                    message=friendship.message
                ))
        
        return FriendRequestListResponse(
            requests=request_responses[:limit],
            total=len(request_responses)
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
async def reject_friend_request(
    request_id: str,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a friend request
    """
    try:
        request_uuid = UUID(request_id)
        
        # Check if request exists
        friendship = friend_repo.find_friendship_by_id(request_uuid)
        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )
        
        # Check if current user is the recipient of the request
        if friendship.friend_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject this request"
            )
        
        # Update friendship status to REJECTED
        from domain.entities import FriendshipStatus
        success = friend_repo.update_friendship_status(request_uuid, FriendshipStatus.REJECTED)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reject friend request"
            )
        
        return {"message": "Friend request rejected"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{user_id}")
async def remove_friend(
    user_id: str,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a friend
    """
    try:
        friend_uuid = UUID(user_id)
        current_user_id = current_user.id
        
        # Delete friendship using repository
        success = friend_repo.delete_friendship(current_user_id, friend_uuid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friendship not found or already removed"
            )
        
        return {"message": "Friend removed successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/block")
async def block_user(
    user_id: str,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Block a user
    """
    try:
        user_uuid = UUID(user_id)
        current_user_id = current_user.id
        
        # For now, we'll implement blocking by creating a BLOCKED friendship entry
        # In a more sophisticated system, you'd have a separate blocking system
        
        from domain.entities import new_friendship, FriendshipStatus
        
        # Create a blocked friendship entry
        blocked_friendship = new_friendship(
            user_id=current_user_id,
            friend_id=user_uuid,
            message="User blocked"
        )
        blocked_friendship.status = FriendshipStatus.BLOCKED
        
        # Save the blocked relationship
        friend_repo.save_friendship(blocked_friendship)
        
        # Also remove any existing friendship
        friend_repo.delete_friendship(current_user_id, user_uuid)
        
        return {"message": "User blocked successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/search")
async def search_users(
    q: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    user_repo = Depends(get_user_repository),
    friend_repo = Depends(get_friend_repository)
):
    """Search for users by display name"""
    try:
        logger.info(f"🔍 User {current_user.display_name} ({current_user.id}) searching for: '{q}'")
        
        if len(q.strip()) < 2:
            return {
                "users": [],
                "query": q,
                "total": 0,
                "message": "Search query must be at least 2 characters"
            }
        
        # Search users by display name
        logger.info(f"🔍 Backend: Searching for users with query: '{q.strip()}'")
        search_results = user_repo.search_by_display_name(
            query=q.strip(),
            limit=limit,
            exclude_user_id=current_user.id
        )
        
        logger.info(f"🔍 Backend: Found {len(search_results)} users from repository")
        
        # Get friendship status for each user
        user_responses = []
        for user in search_results:
            # Check if there's an existing friendship
            friendship_status = "none"  # Default: no relationship
            
            # Check for existing friendship in both directions
            friendships = friend_repo.find_friendships_by_user_id(current_user.id)
            for friendship in friendships:
                if friendship.friend_id == user.id or friendship.user_id == user.id:
                    if friendship.status.name.lower() == "accepted":
                        friendship_status = "friends"
                    elif friendship.status.name.lower() == "pending":
                        if friendship.user_id == current_user.id:
                            friendship_status = "pending_sent"  # Current user sent request
                        else:
                            friendship_status = "pending_received"  # Current user received request
                    elif friendship.status.name.lower() == "blocked":
                        friendship_status = "blocked"
                    break
            
            # Build user response
            profile_image_url = user.profile_image_url
            if profile_image_url and profile_image_url.startswith("/"):
                from infrastructure.config import settings
                profile_image_url = f"{settings.BASE_URL}{profile_image_url}"
            
            user_responses.append({
                "user_id": str(user.id),
                "display_name": user.display_name,
                "profile_image_url": profile_image_url,
                "bio": user.bio,
                "status": "online" if user.status.name.lower() == "online" else "offline",
                "friendship_status": friendship_status,
                "topic_preferences": user.topic_preferences[:5] if user.topic_preferences else []  # Show first 5 topics
            })
        
        logger.info(f"✅ Found {len(user_responses)} users matching '{q}'")
        
        return {
            "users": user_responses,
            "query": q,
            "total": len(user_responses)
        }
        
    except Exception as e:
        logger.error(f"❌ Search failed for query '{q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

@router.get("/recommendations")
async def get_user_recommendations(
    limit: int = 20,
    min_common_interests: int = 1,
    current_user: User = Depends(get_current_user),
    user_repo = Depends(get_user_repository),
    friend_repo = Depends(get_friend_repository)
):
    """Get user recommendations based on similar interests/topics"""
    try:
        logger.info(f"🎯 Getting recommendations for user {current_user.display_name} ({current_user.id})")
        
        # Get current user's interests
        user_interests = current_user.topic_preferences or []
        
        if not user_interests:
            logger.info(f"ℹ️ User {current_user.display_name} has no topic preferences")
            return {
                "users": [],
                "total": 0,
                "message": "No topic preferences set. Join some voice chats to build your interest profile!"
            }
        
        logger.info(f"🔍 Finding users with similar interests to: {user_interests[:5]}..." if len(user_interests) > 5 else f"🔍 Finding users with similar interests to: {user_interests}")
        
        # Find users with similar interests
        similar_users_data = user_repo.find_users_by_interests(
            interests=user_interests,
            limit=limit + 10,  # Get extra to account for filtering
            exclude_user_id=current_user.id,
            min_common_interests=min_common_interests
        )
        
        # Filter out users who are already friends or blocked
        user_responses = []
        existing_friendships = friend_repo.find_friendships_by_user_id(current_user.id)
        
        # Create set of user IDs to exclude (already friends/blocked)
        excluded_user_ids = set()
        for friendship in existing_friendships:
            if friendship.status.name.lower() in ["accepted", "blocked"]:
                other_user_id = friendship.friend_id if friendship.user_id == current_user.id else friendship.user_id
                excluded_user_ids.add(other_user_id)
        
        for user_data in similar_users_data:
            user = user_data["user"]
            
            # Skip if already friends or blocked
            if user.id in excluded_user_ids:
                continue
            
            # Check for pending requests
            friendship_status = "none"
            for friendship in existing_friendships:
                if (friendship.friend_id == user.id or friendship.user_id == user.id) and friendship.status.name.lower() == "pending":
                    if friendship.user_id == current_user.id:
                        friendship_status = "pending_sent"
                    else:
                        friendship_status = "pending_received"
                    break
            
            # Build user response
            profile_image_url = user.profile_image_url
            if profile_image_url and profile_image_url.startswith("/"):
                from infrastructure.config import settings
                profile_image_url = f"{settings.BASE_URL}{profile_image_url}"
            
            user_responses.append({
                "user_id": str(user.id),
                "display_name": user.display_name,
                "profile_image_url": profile_image_url,
                "bio": user.bio,
                "status": "online" if user.status.name.lower() == "online" else "offline",
                "friendship_status": friendship_status,
                "topic_preferences": user.topic_preferences[:5] if user.topic_preferences else [],
                "common_interests": user_data["common_interests"],
                "similarity_score": round(user_data["similarity_score"], 2),
                "total_common_interests": user_data["total_common"]
            })
            
            # Stop when we have enough results
            if len(user_responses) >= limit:
                break
        
        logger.info(f"✅ Found {len(user_responses)} user recommendations")
        
        return {
            "users": user_responses,
            "total": len(user_responses),
            "user_interests": user_interests[:10],  # Show user's interests for context
            "min_common_interests": min_common_interests
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get user recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendations"
        )

@router.delete("/{user_id}/block")
async def unblock_user(
    user_id: str,
    friend_repo = Depends(get_friend_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Unblock a user
    """
    try:
        user_uuid = UUID(user_id)
        current_user_id = current_user.id
        
        # Remove the blocked relationship
        success = friend_repo.delete_friendship(current_user_id, user_uuid)
        
        # For blocking system, we don't strictly require the relationship to exist
        # as the user might have been blocked through other means
        
        return {"message": "User unblocked successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 