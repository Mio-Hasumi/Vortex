"""
Matching Repository implementation using Firebase
"""

import logging
from typing import Optional, List, Dict, Any
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
    
    async def process_timeout_matches(self, timeout_minutes: int = 1) -> List[dict]:
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
                
                # For timeout matches, create a full AI match instead of simple match
                try:
                    # Get hashtags from users if available
                    user1_preferences = user1.get('preferences', {})
                    user2_preferences = user2.get('preferences', {})
                    
                    user1_hashtags = user1_preferences.get('generated_hashtags', []) or user1.get('hashtags', [])
                    user2_hashtags = user2_preferences.get('generated_hashtags', []) or user2.get('hashtags', [])
                    
                    # Use combined hashtags for the timeout match
                    combined_hashtags = list(set(user1_hashtags + user2_hashtags))
                    if not combined_hashtags:
                        combined_hashtags = ['#GeneralChat', '#TimeoutMatch']
                    
                    # Create AI session ID for timeout match
                    ai_session_id = f"timeout_ai_session_{user1_id}_{user2_id}_{datetime.utcnow().timestamp()}"
                    
                    # Create full AI match with room and tokens
                    match_data = await self.create_ai_match(
                        user1_id=user1_id,
                        user2_id=user2_id,
                        hashtags=combined_hashtags,
                        confidence=0.5,  # Moderate confidence for timeout matches
                        ai_session_id=ai_session_id
                    )
                    
                    match_info = {
                        'match_id': match_data['match_id'],
                        'session_id': match_data['session_id'],
                        'room_id': match_data['room_id'],
                        'user1_id': user1_id,
                        'user2_id': user2_id,
                        'match_type': 'timeout_fallback',
                        'wait_time_user1': user1['wait_time_seconds'],
                        'wait_time_user2': user2['wait_time_seconds'],
                        'hashtags': combined_hashtags,
                        'confidence': 0.5,
                        'match_data': match_data  # Include full match data for WebSocket notifications
                    }
                    
                    matches_created.append(match_info)
                    
                    logger.info(f"✅ Timeout match created: {user1_id} + {user2_id} (waited {user1['wait_time_seconds']:.0f}s and {user2['wait_time_seconds']:.0f}s)")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create timeout AI match for {user1_id} + {user2_id}: {e}")
                    continue
            
            return matches_created
            
        except Exception as e:
            logger.error(f"❌ Failed to process timeout matches: {e}")
            return []
    
    def find_users_by_hashtags(self, hashtags: List[str], exclude_user_id: str = None, max_results: int = 10, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """
        Find users by hashtags for AI matching
        
        Args:
            hashtags: List of hashtags to match
            exclude_user_id: User ID to exclude from results
            max_results: Maximum number of users to return
            min_similarity: Minimum similarity score required
            
        Returns:
            List of matching users with their hashtags and similarity scores
        """
        try:
            logger.info(f"🔍 Finding users by hashtags: {hashtags}")
            logger.info(f"🔍 Excluding user: {exclude_user_id}")
            
            # Get users from matching queue
            queue_users = self.redis.get_queue_status()
            logger.info(f"🔍 Found {len(queue_users)} users in queue")
            
            matching_users = []
            
            for user_data in queue_users:
                user_id = user_data.get('user_id')
                if user_id == exclude_user_id:
                    logger.info(f"🔍 Skipping excluded user: {user_id}")
                    continue
                    
                user_preferences = user_data.get('preferences', {})
                
                # For AI matching, use generated_hashtags directly (not preferred_topics)
                user_hashtags = user_preferences.get('generated_hashtags', [])
                
                # Fallback: if no generated_hashtags, try to get from the top-level hashtags
                if not user_hashtags:
                    user_hashtags = user_data.get('hashtags', [])
                
                logger.info(f"🔍 User {user_id} hashtags: {user_hashtags}")
                
                # Calculate match score based on hashtag overlap
                if user_hashtags:
                    overlap = set(hashtags) & set(user_hashtags)
                    logger.info(f"🔍 Hashtag overlap: {list(overlap)}")
                    
                    if overlap:
                        similarity = len(overlap) / max(len(hashtags), len(user_hashtags))
                        logger.info(f"🔍 Similarity score: {similarity:.2f} (min required: {min_similarity})")
                        
                        if similarity >= min_similarity:
                            matching_users.append({
                                'user_id': user_id,
                                'hashtags': user_hashtags,
                                'similarity': similarity,
                                'match_score': similarity,  # For backward compatibility
                                'overlapping_hashtags': list(overlap)
                            })
                            logger.info(f"✅ Added matching user: {user_id} (similarity: {similarity:.2f})")
                        else:
                            logger.info(f"❌ User {user_id} similarity too low: {similarity:.2f}")
                    else:
                        logger.info(f"❌ No hashtag overlap with user {user_id}")
                else:
                    logger.info(f"❌ User {user_id} has no hashtags")
            
            # Sort by similarity and return top matches
            matching_users.sort(key=lambda x: x['similarity'], reverse=True)
            result = matching_users[:max_results]
            
            logger.info(f"✅ Found {len(result)} users matching hashtags")
            for user in result:
                logger.info(f"   👤 {user['user_id']}: {user['similarity']:.2f} similarity")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to find users by hashtags: {e}")
            return []

    def add_to_ai_queue(self, user_id: str, hashtags: List[str] = None, voice_input: str = None, ai_session_id: str = None, ai_analysis: Dict[str, Any] = None):
        """
        Add user to AI matching queue with analysis data
        
        Args:
            user_id: User ID
            hashtags: Generated hashtags for matching
            voice_input: Original voice input text
            ai_session_id: AI session ID
            ai_analysis: AI analysis results (topics, hashtags, etc.)
        """
        try:
            logger.info(f"🧠 Adding user {user_id} to AI matching queue")
            
            # Get the actual hashtags and topics
            final_hashtags = hashtags or (ai_analysis.get('generated_hashtags', []) if ai_analysis else [])
            final_topics = ai_analysis.get('extracted_topics', []) if ai_analysis else []
            
            logger.info(f"🧠 User hashtags: {final_hashtags}")
            logger.info(f"🧠 User topics: {final_topics}")
            
            # Store AI analysis data with the queue entry
            queue_data = {
                'user_id': user_id,
                'hashtags': final_hashtags,  # Store hashtags at top level for easy access
                'voice_input': voice_input or (ai_analysis.get('understood_text', '') if ai_analysis else ''),
                'ai_session_id': ai_session_id,
                'preferences': {
                    'preferred_topics': final_topics,  # Store actual topics here
                    'generated_hashtags': final_hashtags,  # Store hashtags here too for backup
                    'match_intent': voice_input or (ai_analysis.get('match_intent', '') if ai_analysis else ''),
                    'language_preference': 'en-US'
                },
                'ai_analysis': ai_analysis or {},
                'queue_type': 'ai_matching',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Use Redis to store the complete AI queue entry directly
            # This ensures the data structure is exactly what we expect
            success = self.redis.enqueue('matching_queue', queue_data, priority=0)
            
            if success:
                logger.info(f"✅ User {user_id} added to AI matching queue with hashtags: {final_hashtags}")
            else:
                logger.error(f"❌ Failed to add user {user_id} to Redis queue")
                
        except Exception as e:
            logger.error(f"❌ Failed to add user to AI queue: {e}")
            raise

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
    
    async def create_ai_match(self, user1_id: str, user2_id: str, hashtags: List[str], confidence: float, ai_session_id: str) -> Dict[str, Any]:
        """
        Create an AI-hosted match between two users
        
        Args:
            user1_id: First user ID (string)
            user2_id: Second user ID (string)
            hashtags: Matching hashtags
            confidence: Match confidence score
            ai_session_id: AI session ID
            
        Returns:
            Match information dictionary
        """
        try:
            logger.info(f"🤖 Creating AI match: {user1_id} + {user2_id} (confidence: {confidence:.2f})")
            
            # Import here to avoid circular imports
            from infrastructure.container import container
            
            # Get repositories
            room_repo = container.get_room_repository()
            user_repo = container.get_user_repository()
            
            # Convert string IDs to UUIDs
            user1_uuid = UUID(user1_id)
            user2_uuid = UUID(user2_id)
            
            # Create LiveKit room for the match
            room_name = f"ai_match_{user1_id[:8]}_{user2_id[:8]}_{int(datetime.utcnow().timestamp())}"
            
            # Ensure all hashtags are strings
            hashtags_str = [str(tag) for tag in hashtags]
            
            # Create room entity
            from api.routers.rooms import create_room_entity
            room = create_room_entity(
                name=f"AI Chat: {', '.join(hashtags_str[:2])}",
                topic=', '.join(hashtags_str),
                created_by=user1_uuid,
                max_participants=3,  # 2 users + 1 AI host
                is_private=False
            )
            
            # Save room to repository
            saved_room = await room_repo.save(room)
            
            # Add both users as participants
            room_repo.add_participant(saved_room.id, user1_uuid)
            room_repo.add_participant(saved_room.id, user2_uuid)
            
            # Create match record
            match = Match(
                id=uuid4(),
                user_id=user1_uuid,
                preferred_topics=[],  # AI matches don't use traditional topics
                max_participants=2,
                status=MatchStatus.MATCHED,
                matched_users=[user2_uuid],
                matched_at=datetime.utcnow(),
                room_id=saved_room.id
            )
            
            # Save match
            saved_match = self.save_match(match)
            
            # Generate LiveKit tokens for both users
            user1_token = room_repo.generate_livekit_token(saved_room.id, user1_uuid)
            user2_token = room_repo.generate_livekit_token(saved_room.id, user2_uuid)
            
            # Get user information for participant data
            user1_info = user_repo.find_by_id(user1_uuid)
            user2_info = user_repo.find_by_id(user2_uuid)
            
            # Remove users from matching queue
            self.remove_from_queue(user1_uuid)
            self.remove_from_queue(user2_uuid)
            
            # Prepare match data
            match_data = {
                "match_id": str(saved_match.id),
                "session_id": ai_session_id,
                "room_id": str(saved_room.id),
                "livekit_room_name": saved_room.livekit_room_name,
                "hashtags": hashtags_str,  # Use string version of hashtags
                "confidence": confidence,
                "created_at": datetime.utcnow().isoformat(),
                "users": {
                    user1_id: {
                        "livekit_token": user1_token,
                        "display_name": user1_info.display_name if user1_info else "User 1",
                        "participants": [
                            {
                                "user_id": user1_id,
                                "display_name": user1_info.display_name if user1_info else "User 1", 
                                "is_current_user": True
                            },
                            {
                                "user_id": user2_id,
                                "display_name": user2_info.display_name if user2_info else "User 2",
                                "is_current_user": False
                            }
                        ]
                    },
                    user2_id: {
                        "livekit_token": user2_token,
                        "display_name": user2_info.display_name if user2_info else "User 2",
                        "participants": [
                            {
                                "user_id": user1_id,
                                "display_name": user1_info.display_name if user1_info else "User 1",
                                "is_current_user": False
                            },
                            {
                                "user_id": user2_id, 
                                "display_name": user2_info.display_name if user2_info else "User 2",
                                "is_current_user": True
                            }
                        ]
                    }
                }
            }
            
            logger.info(f"✅ AI match created successfully:")
            logger.info(f"   🆔 Match ID: {saved_match.id}")
            logger.info(f"   🏠 Room ID: {saved_room.id}")
            logger.info(f"   🏷️ Hashtags: {hashtags}")
            
            return match_data
            
        except Exception as e:
            logger.error(f"❌ Failed to create AI match: {e}")
            logger.exception("Full exception details:")
            raise
    
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