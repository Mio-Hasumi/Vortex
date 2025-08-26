"""
Friend Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

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
        Find all friendships for a user (both directions)
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of friendship entities
        """
        try:
            # Find friendships where user is the initiator
            friendships_as_user = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)},
                    {"field": "status", "operator": "==", "value": "accepted"}
                ],
                order_by="created_at"
            )
            
            # Find friendships where user is the recipient
            friendships_as_friend = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "friend_id", "operator": "==", "value": str(user_id)},
                    {"field": "status", "operator": "==", "value": "accepted"}
                ],
                order_by="created_at"
            )
            
            # Combine both lists and convert to entities
            all_friendships_data = friendships_as_user + friendships_as_friend
            friendships = [self._dict_to_friendship(data) for data in all_friendships_data]
            
            return friendships
            
        except Exception as e:
            logger.error(f"❌ Failed to find friendships for user {user_id}: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            return []
    
    def find_all_friendships_by_user_id(self, user_id: UUID) -> List[Friendship]:
        """
        Find ALL friendships for a user regardless of status (used for search)
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of all friendship entities (accepted, pending, blocked, etc.)
        """
        try:
            # Find friendships where user is the initiator
            friendships_as_user = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)}
                ],
                order_by="created_at"
            )
            
            # Find friendships where user is the recipient
            friendships_as_friend = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "friend_id", "operator": "==", "value": str(user_id)}
                ],
                order_by="created_at"
            )
            
            # Combine both lists and convert to entities
            all_friendships_data = friendships_as_user + friendships_as_friend
            friendships = [self._dict_to_friendship(data) for data in all_friendships_data]
            
            return friendships
            
        except Exception as e:
            logger.error(f"❌ Failed to find all friendships for user {user_id}: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
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

    def find_pending_sent_requests_by_user_id(self, user_id: UUID) -> List[Friendship]:
        """Find pending friend requests sent by the user"""
        try:
            requests_data = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)},
                    {"field": "status", "operator": "==", "value": "pending"}
                ],
                order_by="created_at",
            )

            return [self._dict_to_friendship(data) for data in requests_data]

        except Exception as e:
            logger.error(f"❌ Failed to find pending sent requests for user {user_id}: {e}")
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
        Delete a friendship relationship
        
        Args:
            user_id: User's UUID
            friend_id: Friend's UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🗑️ Deleting friendship between {user_id} and {friend_id}")
            
            # Find friendships between these two users (in both directions)
            friendships_data = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)},
                    {"field": "friend_id", "operator": "==", "value": str(friend_id)}
                ]
            )
            
            # Also check the reverse direction
            reverse_friendships = self.firebase.query_documents(
                self.friends_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(friend_id)},
                    {"field": "friend_id", "operator": "==", "value": str(user_id)}
                ]
            )
            
            all_friendships = friendships_data + reverse_friendships
            
            # Delete all found friendships
            for friendship_data in all_friendships:
                self.firebase.delete_document(
                    self.friends_collection,
                    friendship_data["id"]
                )
                logger.info(f"🗑️ Deleted friendship document: {friendship_data['id']}")
            
            logger.info(f"✅ Friendship deletion completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete friendship: {e}")
            return False

    def block_user(self, user_id: UUID, target_user_id: UUID) -> bool:
        """
        Block a user by creating a blocked friendship entry
        
        Args:
            user_id: User's UUID (the one doing the blocking)
            target_user_id: Target user's UUID (the one being blocked)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🚫 User {user_id} blocking user {target_user_id}")
            
            # First, remove any existing friendship
            self.delete_friendship(user_id, target_user_id)
            
            # Create a blocked friendship entry
            blocked_friendship = new_friendship(
                user_id=user_id,
                friend_id=target_user_id,
                message="User blocked"
            )
            blocked_friendship.status = FriendshipStatus.BLOCKED
            
            # Save the blocked relationship
            self.save_friendship(blocked_friendship)
            
            logger.info(f"✅ User {user_id} successfully blocked user {target_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to block user {target_user_id}: {e}")
            return False

    def unfriend_user(self, user_id: UUID, target_user_id: UUID) -> bool:
        """
        Unfriend a user by removing the friendship relationship
        
        Args:
            user_id: User's UUID (the one doing the unfriending)
            target_user_id: Target user's UUID (the one being unfriended)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"👋 User {user_id} unfriending user {target_user_id}")
            
            # Find and delete the friendship
            success = self.delete_friendship(user_id, target_user_id)
            
            if success:
                logger.info(f"✅ User {user_id} successfully unfriended user {target_user_id}")
            else:
                logger.warning(f"⚠️ Unfriending may have failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to unfriend user {target_user_id}: {e}")
            return False

    def unblock_user(self, user_id: UUID, target_user_id: UUID) -> bool:
        """
        Unblock a user by removing the blocked friendship entry
        
        Args:
            user_id: User's UUID (the one doing the unblocking)
            target_user_id: Target user's UUID (the one being unblocked)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔓 User {user_id} unblocking user {target_user_id}")
            
            # Find and delete the blocked friendship
            success = self.delete_friendship(user_id, target_user_id)
            
            if success:
                logger.info(f"✅ User {user_id} successfully unblocked user {target_user_id}")
            else:
                logger.warning(f"⚠️ Unblocking may have failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to unblock user {target_user_id}: {e}")
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
        try:
            # Check required fields
            required_fields = ["id", "user_id", "friend_id", "status", "created_at"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Convert status
            status_str = data["status"].upper()
            
            # Handle created_at (string)
            created_at = self._parse_datetime(data["created_at"], "created_at")
            
            # Handle accepted_at (could be Firebase timestamp or string)
            accepted_at = None
            if data.get("accepted_at"):
                accepted_at = self._parse_datetime(data["accepted_at"], "accepted_at")
            
            friendship = Friendship(
                id=UUID(data["id"]),
                user_id=UUID(data["user_id"]),
                friend_id=UUID(data["friend_id"]),
                status=FriendshipStatus[status_str],
                created_at=created_at,
                accepted_at=accepted_at,
                message=data.get("message")
            )
            
            return friendship
            
        except Exception as e:
            logger.error(f"❌ [FriendRepo] Failed to convert dict to friendship: {e}")
            logger.error(f"❌ [FriendRepo] Raw data: {data}")
            raise
    
    def _parse_datetime(self, value, field_name: str) -> datetime:
        """Parse datetime from various formats (string, Firebase timestamp)"""
        try:
            # If it's already a datetime object, return it
            if isinstance(value, datetime):
                return value
            
            # If it's a string, parse as ISO format
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            
            # If it's a Firebase timestamp object
            if hasattr(value, 'seconds') and hasattr(value, 'nanoseconds'):
                # Firebase timestamp - convert to datetime
                timestamp_seconds = value.seconds + (value.nanoseconds / 1e9)
                return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
            
            # If it's a dictionary with _seconds (Firestore timestamp format)
            if isinstance(value, dict) and '_seconds' in value:
                timestamp_seconds = value['_seconds']
                nanoseconds = value.get('_nanoseconds', 0)
                total_seconds = timestamp_seconds + (nanoseconds / 1e9)
                return datetime.fromtimestamp(total_seconds, tz=timezone.utc)
            
            # Try to parse as timestamp (seconds since epoch)
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
                
            raise ValueError(f"Unknown datetime format for {field_name}: {type(value)} - {value}")
            
        except Exception as e:
            logger.error(f"❌ [FriendRepo] Failed to parse {field_name}: {e}")
            logger.error(f"❌ [FriendRepo] Value type: {type(value)}, Value: {value}")
            raise

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