"""
Friend Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from domain.entities import Friendship, FriendshipStatus
from infrastructure.db.firebase import FirebaseAdminService

logger = logging.getLogger(__name__)


class FriendRepository:
    """
    Friend repository implementation using Firebase Firestore
    """
    
    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.friends_collection = "friendships"
    
    def save_friendship(self, friendship: Friendship) -> Friendship:
        """
        Save friendship relationship to Firebase Firestore
        
        Args:
            friendship: Friendship entity to save
            
        Returns:
            Saved friendship entity
        """
        try:
            friendship_data = self._friendship_to_dict(friendship)
            
            # Save to Firestore
            self.firebase.add_document(
                self.friends_collection,
                friendship_data,
                str(friendship.id)
            )
            
            logger.info(f"✅ Friendship saved: {friendship.id}")
            return friendship
            
        except Exception as e:
            logger.error(f"❌ Failed to save friendship {friendship.id}: {e}")
            raise
    
    def find_friendships_by_user_id(self, user_id: UUID) -> List[Friendship]:
        """
        Find all friendships for a user
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of friendship entities
        """
        try:
            friendships_data = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)},
                    {"field": "status", "operator": "==", "value": "accepted"}
                ],
                order_by="created_at"
            )
            
            return [self._dict_to_friendship(data) for data in friendships_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find friendships for user {user_id}: {e}")
            return []
    
    def find_pending_requests_by_user_id(self, user_id: UUID) -> List[Friendship]:
        """
        Find pending friend requests for a user
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of pending friendship entities
        """
        try:
            requests_data = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "friend_id", "operator": "==", "value": str(user_id)},
                    {"field": "status", "operator": "==", "value": "pending"}
                ],
                order_by="created_at"
            )
            
            return [self._dict_to_friendship(data) for data in requests_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find pending requests for user {user_id}: {e}")
            return []
    
    def find_friendship_by_id(self, friendship_id: UUID) -> Optional[Friendship]:
        """
        Find friendship by ID
        
        Args:
            friendship_id: Friendship UUID
            
        Returns:
            Friendship entity or None
        """
        try:
            friendship_data = self.firebase.get_document(
                self.friends_collection,
                str(friendship_id)
            )
            
            if friendship_data:
                return self._dict_to_friendship(friendship_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find friendship {friendship_id}: {e}")
            return None
    
    def update_friendship_status(self, friendship_id: UUID, status: FriendshipStatus) -> bool:
        """
        Update friendship status
        
        Args:
            friendship_id: Friendship UUID
            status: New status
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                "status": status.name.lower(),
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            if status == FriendshipStatus.ACCEPTED:
                update_data["accepted_at"] = self.firebase.get_server_timestamp()
            
            self.firebase.update_document(
                self.friends_collection,
                str(friendship_id),
                update_data
            )
            
            logger.info(f"✅ Friendship {friendship_id} status updated to {status.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update friendship {friendship_id}: {e}")
            return False
    
    def delete_friendship(self, user_id: UUID, friend_id: UUID) -> bool:
        """
        Delete friendship relationship
        
        Args:
            user_id: User's UUID
            friend_id: Friend's UUID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Find and delete the friendship record
            friendships_data = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)},
                    {"field": "friend_id", "operator": "==", "value": str(friend_id)}
                ]
            )
            
            for friendship_data in friendships_data:
                self.firebase.delete_document(
                    self.friends_collection,
                    friendship_data["id"]
                )
            
            logger.info(f"✅ Friendship deleted: {user_id} - {friend_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete friendship: {e}")
            return False
    
    def _friendship_to_dict(self, friendship: Friendship) -> dict:
        """Convert Friendship entity to dictionary"""
        return {
            "id": str(friendship.id),
            "user_id": str(friendship.user_id),
            "friend_id": str(friendship.friend_id),
            "status": friendship.status.name.lower(),
            "created_at": friendship.created_at.isoformat(),
            "accepted_at": friendship.accepted_at.isoformat() if friendship.accepted_at else None,
            "message": friendship.message
        }
    
    def _dict_to_friendship(self, data: dict) -> Friendship:
        """Convert dictionary to Friendship entity"""
        return Friendship(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            friend_id=UUID(data["friend_id"]),
            status=FriendshipStatus[data["status"].upper()],
            created_at=datetime.fromisoformat(data["created_at"]),
            accepted_at=datetime.fromisoformat(data["accepted_at"]) if data.get("accepted_at") else None,
            message=data.get("message")
        )

# Helper function to create a new friendship
def new_friendship(user_id: UUID, friend_id: UUID, message: str = None) -> Friendship:
    """Create a new friendship entity"""
    return Friendship(
        id=uuid4(),
        user_id=user_id,
        friend_id=friend_id,
        status=FriendshipStatus.PENDING,
        message=message
    ) 