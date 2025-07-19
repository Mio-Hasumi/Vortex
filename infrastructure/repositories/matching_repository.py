"""
Matching Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from domain.entities import Match, MatchStatus
from infrastructure.db.firebase import FirebaseAdminService
from infrastructure.redis.redis_service import RedisService

logger = logging.getLogger(__name__)


class MatchingRepository:
    """
    Matching repository implementation using Firebase Firestore and Redis
    """
    
    def __init__(self, firebase_service: FirebaseAdminService, redis_service: RedisService):
        self.firebase = firebase_service
        self.redis = redis_service
        self.matches_collection = "matches"
        self.match_queue_collection = "match_queue"
    
    def save_match(self, match: Match) -> Match:
        """
        Save match to Firebase Firestore
        
        Args:
            match: Match entity to save
            
        Returns:
            Saved match entity
        """
        try:
            match_data = self._entity_to_dict(match)
            
            # Save to Firestore
            self.firebase.add_document(
                self.matches_collection,
                match_data,
                str(match.id)
            )
            
            logger.info(f"✅ Match saved successfully: {match.id}")
            return match
            
        except Exception as e:
            logger.error(f"❌ Failed to save match {match.id}: {e}")
            raise
    
    def find_match_by_id(self, match_id: UUID) -> Optional[Match]:
        """
        Find match by ID
        
        Args:
            match_id: Match's UUID
            
        Returns:
            Match entity or None if not found
        """
        try:
            match_data = self.firebase.get_document(
                self.matches_collection,
                str(match_id)
            )
            
            if match_data:
                return self._dict_to_entity(match_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find match {match_id}: {e}")
            return None
    
    def find_matches_by_user_id(self, user_id: UUID, limit: int = 20) -> List[Match]:
        """
        Find matches for a user
        
        Args:
            user_id: User's UUID
            limit: Maximum number of matches to return
            
        Returns:
            List of match entities
        """
        try:
            matches_data = self.firebase.query_documents(
                self.matches_collection,
                filters=[
                    {"field": "user_id", "operator": "==", "value": str(user_id)}
                ],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(data) for data in matches_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find matches for user {user_id}: {e}")
            return []
    
    def get_queue_size(self) -> int:
        """
        Get total queue size
        
        Returns:
            Total number of pending requests
        """
        try:
            return self.redis.get_matching_queue_size()
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue size: {e}")
            return 0
    
    def get_queue_position(self, user_id: UUID) -> int:
        """
        Get user's position in the matching queue
        
        Args:
            user_id: User's UUID
            
        Returns:
            Position in queue (0 if not in queue)
        """
        try:
            return self.redis.get_matching_queue_position(user_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue position for user {user_id}: {e}")
            return 0
    
    def add_to_queue(self, user_id: UUID, preferences: dict) -> bool:
        """
        Add user to matching queue
        
        Args:
            user_id: User's UUID
            preferences: User's matching preferences
            
        Returns:
            True if successfully added to queue
        """
        try:
            return self.redis.add_to_matching_queue(user_id, preferences)
            
        except Exception as e:
            logger.error(f"❌ Failed to add user {user_id} to queue: {e}")
            return False
    
    def remove_from_queue(self, user_id: UUID) -> bool:
        """
        Remove user from matching queue
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successfully removed from queue
        """
        try:
            return self.redis.remove_from_matching_queue(user_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to remove user {user_id} from queue: {e}")
            return False
    
    def process_timeout_matches(self, timeout_minutes: int = 1) -> List[dict]:
        """
        Process users who have been waiting too long and randomly match them
        
        Args:
            timeout_minutes: Timeout in minutes before random matching
            
        Returns:
            List of created matches
        """
        try:
            # Get users waiting too long
            timeout_users = self.redis.get_users_waiting_too_long(timeout_minutes)
            
            if len(timeout_users) < 2:
                return []
            
            logger.info(f"🕐 Found {len(timeout_users)} users waiting over {timeout_minutes} minute(s)")
            
            matches_created = []
            
            # Randomly pair users (simple approach: pair in order)
            for i in range(0, len(timeout_users) - 1, 2):
                user1 = timeout_users[i]
                user2 = timeout_users[i + 1]
                
                user1_id = user1['user_id']
                user2_id = user2['user_id']
                
                # Create the timeout match
                if self.redis.create_timeout_match(user1_id, user2_id):
                    # Create a Match entity and save it
                    match = Match(
                        id=uuid4(),
                        user_id=UUID(user1_id),
                        preferred_topics=[],  # No specific topics for timeout match
                        max_participants=2,
                        status=MatchStatus.MATCHED,
                        matched_users=[UUID(user2_id)],
                        matched_at=datetime.utcnow()
                    )
                    
                    # Save to database
                    saved_match = self.save_match(match)
                    
                    match_info = {
                        'match_id': str(saved_match.id),
                        'user1_id': user1_id,
                        'user2_id': user2_id,
                        'match_type': 'timeout_fallback',
                        'wait_time_user1': user1['wait_time_seconds'],
                        'wait_time_user2': user2['wait_time_seconds']
                    }
                    
                    matches_created.append(match_info)
                    
                    logger.info(f"✅ Timeout match created: {user1_id} + {user2_id} (waited {user1['wait_time_seconds']:.0f}s and {user2['wait_time_seconds']:.0f}s)")
            
            return matches_created
            
        except Exception as e:
            logger.error(f"❌ Failed to process timeout matches: {e}")
            return []
    
    def get_timeout_users_count(self, timeout_minutes: int = 1) -> int:
        """
        Get count of users waiting longer than timeout
        
        Args:
            timeout_minutes: Timeout in minutes
            
        Returns:
            Number of users waiting too long
        """
        try:
            timeout_users = self.redis.get_users_waiting_too_long(timeout_minutes)
            return len(timeout_users)
        except Exception as e:
            logger.error(f"❌ Failed to get timeout users count: {e}")
            return 0
    
    def _entity_to_dict(self, match: Match) -> dict:
        """Convert Match entity to dictionary"""
        return {
            "id": str(match.id),
            "user_id": str(match.user_id),
            "preferred_topics": [str(t) for t in match.preferred_topics],
            "max_participants": match.max_participants,
            "language_preference": match.language_preference,
            "status": match.status.name.lower(),
            "created_at": match.created_at.isoformat(),
            "matched_at": match.matched_at.isoformat() if match.matched_at else None,
            "expired_at": match.expired_at.isoformat() if match.expired_at else None,
            "matched_users": [str(u) for u in match.matched_users],
            "selected_topic_id": str(match.selected_topic_id) if match.selected_topic_id else None,
            "room_id": str(match.room_id) if match.room_id else None
        }
    
    def _dict_to_entity(self, data: dict) -> Match:
        """Convert dictionary to Match entity"""
        return Match(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            preferred_topics=[UUID(t) for t in data.get("preferred_topics", [])],
            max_participants=data.get("max_participants", 3),
            language_preference=data.get("language_preference"),
            status=MatchStatus[data["status"].upper()],
            created_at=datetime.fromisoformat(data["created_at"]),
            matched_at=datetime.fromisoformat(data["matched_at"]) if data.get("matched_at") else None,
            expired_at=datetime.fromisoformat(data["expired_at"]) if data.get("expired_at") else None,
            matched_users=[UUID(u) for u in data.get("matched_users", [])],
            selected_topic_id=UUID(data["selected_topic_id"]) if data.get("selected_topic_id") else None,
            room_id=UUID(data["room_id"]) if data.get("room_id") else None
        )

# Helper function to create a new match
def new_match(user_id: UUID, preferred_topics: List[str], max_participants: int = 3) -> Match:
    """Create a new match entity"""
    # Convert topic strings to UUIDs (for now, generate random UUIDs)
    topic_uuids = [uuid4() for _ in preferred_topics]
    
    return Match(
        id=uuid4(),
        user_id=user_id,
        preferred_topics=topic_uuids,
        max_participants=max_participants,
        status=MatchStatus.PENDING
    ) 