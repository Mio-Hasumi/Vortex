"""
User Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID

from domain.entities import User, UserStatus
from infrastructure.db.firebase import FirebaseAdminService

logger = logging.getLogger(__name__)


class UserRepository:
    """
    User repository implementation using Firebase Firestore
    """
    
    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.collection_name = "users"
    
    def save(self, user: User) -> User:
        """
        Save user to Firebase Firestore
        
        Args:
            user: User entity to save
            
        Returns:
            Saved user entity
        """
        try:
            user_data = self._entity_to_dict(user)
            
            # Save to Firestore
            self.firebase.add_document(
                self.collection_name,
                user_data,
                str(user.id)
            )
            
            logger.info(f"✅ User saved successfully: {user.id}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Failed to save user {user.id}: {e}")
            raise
    
    def find_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Find user by ID
        
        Args:
            user_id: User's UUID
            
        Returns:
            User entity or None if not found
        """
        try:
            user_data = self.firebase.get_document(
                self.collection_name,
                str(user_id)
            )
            
            if user_data:
                return self._dict_to_entity(user_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find user {user_id}: {e}")
            return None
    
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email
        
        Args:
            email: User's email address
            
        Returns:
            User entity or None if not found
        """
        try:
            users = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "email", "operator": "==", "value": email.lower()}],
                limit=1
            )
            
            if users:
                return self._dict_to_entity(users[0])
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find user by email {email}: {e}")
            return None
    
    def find_by_phone_number(self, phone_number: str) -> Optional[User]:
        """
        Find user by phone number
        
        Args:
            phone_number: User's phone number
            
        Returns:
            User entity or None if not found
        """
        try:
            users = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "phone_number", "operator": "==", "value": phone_number}],
                limit=1
            )
            
            if users:
                return self._dict_to_entity(users[0])
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find user by phone number {phone_number}: {e}")
            return None
    
    def find_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """
        Find user by Firebase UID
        
        Args:
            firebase_uid: Firebase Auth UID
            
        Returns:
            User entity or None if not found
        """
        try:
            users = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "firebase_uid", "operator": "==", "value": firebase_uid}],
                limit=1
            )
            
            if users:
                return self._dict_to_entity(users[0])
            
            # If the user does not exist, create a new user record for the real Firebase user
            # This applies to users logging in for the first time
            logger.info(f"Creating new user for Firebase UID: {firebase_uid}")
            from uuid import uuid4
            new_user = User(
                id=uuid4(),  # Generate a new UUID
                firebase_uid=firebase_uid,
                email=f"user_{firebase_uid}@firebase.com",  # Temporary email, can be updated later
                display_name=f"User {firebase_uid[:8]}",
                is_active=True,
                status=UserStatus.ONLINE,
                password_hash=""  # Default empty password hash
            )
            
            # Save to database
            saved_user = self.save(new_user)
            return saved_user
            
        except Exception as e:
            logger.error(f"❌ Failed to find user by Firebase UID {firebase_uid}: {e}")
            return None
    
    def find_by_display_name(self, display_name: str) -> Optional[User]:
        """
        Find user by display name
        
        Args:
            display_name: User's display name
            
        Returns:
            User entity or None if not found
        """
        try:
            users = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "display_name", "operator": "==", "value": display_name}],
                limit=1
            )
            
            if users:
                return self._dict_to_entity(users[0])
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find user by display name {display_name}: {e}")
            return None
    
    def search_by_display_name(self, query: str, limit: int = 20, exclude_user_id: UUID = None) -> List[User]:
        """
        Search users by display name (partial match)
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            exclude_user_id: User ID to exclude from results (usually current user)
            
        Returns:
            List of matching User entities
        """
        try:
            logger.info(f"🔍 Searching users by display name: '{query}' (limit: {limit})")
            
            # Since Firebase doesn't support LIKE queries, we'll get all users and filter in memory
            # This is simpler and more reliable for small to medium user bases
            all_users = self.firebase.query_documents(
                self.collection_name,
                limit=200  # Reasonable limit to avoid performance issues
            )
            
            logger.info(f"🔍 Repository: Retrieved {len(all_users)} total users from database")
            
            query_lower = query.lower().strip()
            if len(query_lower) < 2:
                logger.warning(f"⚠️ Search query too short: '{query}' (minimum 2 characters)")
                return []
            
            results = []
            for user_data in all_users:
                try:
                    user = self._dict_to_entity(user_data)
                    logger.info(f"🔍 Repository: Processing user: {user.display_name} (ID: {user.id})")
                    
                    # Exclude current user if specified
                    if exclude_user_id and user.id == exclude_user_id:
                        logger.info(f"🔍 Repository: Excluding current user: {user.display_name}")
                        continue
                    
                    # Check if display name contains the search query (case-insensitive)
                    if query_lower in user.display_name.lower():
                        logger.info(f"🔍 Repository: ✅ User matches query: {user.display_name}")
                        results.append(user)
                        
                        # Stop if we have enough results
                        if len(results) >= limit:
                            break
                    else:
                        logger.info(f"🔍 Repository: ❌ User doesn't match query: {user.display_name} (query: '{query_lower}')")
                except Exception as user_error:
                    logger.error(f"🔍 Repository: Error processing user data: {user_error}")
                    continue
            
            logger.info(f"✅ Found {len(results)} users matching '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search users by display name '{query}': {e}")
            return []
    
    def find_users_by_interests(self, interests: List[str], limit: int = 20, exclude_user_id: UUID = None, min_common_interests: int = 1) -> List[dict]:
        """
        Find users with similar interests/topics
        
        Args:
            interests: List of interest/topic strings to match
            limit: Maximum number of results to return
            exclude_user_id: User ID to exclude from results
            min_common_interests: Minimum number of common interests required
            
        Returns:
            List of user data with similarity scores
        """
        try:
            logger.info(f"🎯 Finding users with similar interests: {interests[:3]}..." if len(interests) > 3 else f"🎯 Finding users with similar interests: {interests}")
            
            # Get all users (we'll filter by interests in memory since Firebase doesn't support complex array queries)
            all_users = self.firebase.query_documents(
                self.collection_name,
                limit=200  # Reasonable limit to avoid performance issues
            )
            
            matching_users = []
            interests_set = set(interest.lower() for interest in interests)
            
            for user_data in all_users:
                user = self._dict_to_entity(user_data)
                
                # Exclude current user
                if exclude_user_id and user.id == exclude_user_id:
                    continue
                
                # Get user's interests (from topic_preferences field)
                user_interests = user.topic_preferences or []
                user_interests_set = set(interest.lower() for interest in user_interests)
                
                # Calculate similarity
                common_interests = interests_set.intersection(user_interests_set)
                
                if len(common_interests) >= min_common_interests:
                    # Calculate similarity score (Jaccard similarity)
                    union_interests = interests_set.union(user_interests_set)
                    similarity_score = len(common_interests) / len(union_interests) if union_interests else 0
                    
                    matching_users.append({
                        "user": user,
                        "common_interests": list(common_interests),
                        "similarity_score": similarity_score,
                        "total_common": len(common_interests)
                    })
            
            # Sort by similarity score (descending) and then by number of common interests
            matching_users.sort(key=lambda x: (x["similarity_score"], x["total_common"]), reverse=True)
            
            # Limit results
            results = matching_users[:limit]
            
            logger.info(f"✅ Found {len(results)} users with similar interests")
            for result in results[:3]:  # Log first 3 for debugging
                user = result["user"]
                logger.info(f"   👤 {user.display_name}: {result['similarity_score']:.2f} similarity, {result['total_common']} common interests")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to find users by interests: {e}")
            return []
    
    def update(self, user: User) -> User:
        """
        Update user in Firebase Firestore
        
        Args:
            user: User entity to update
            
        Returns:
            Updated user entity
        """
        try:
            user_data = self._entity_to_dict(user)
            
            # Remove ID from data (it's the document ID)
            user_data.pop('id', None)
            
            # Update in Firestore
            self.firebase.update_document(
                self.collection_name,
                str(user.id),
                user_data
            )
            
            logger.info(f"✅ User updated successfully: {user.id}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Failed to update user {user.id}: {e}")
            raise
    
    def delete(self, user_id: UUID) -> None:
        """
        Delete user from Firebase Firestore
        
        Args:
            user_id: User's UUID
        """
        try:
            # Soft delete - mark as inactive
            self.firebase.update_document(
                self.collection_name,
                str(user_id),
                {"is_active": False}
            )
            
            logger.info(f"✅ User deleted (soft) successfully: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete user {user_id}: {e}")
            raise
    
    def find_active_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """
        Find active users
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of active user entities
        """
        try:
            users_data = self.firebase.query_documents(
                self.collection_name,
                filters=[("is_active", "==", True)],
                limit=limit,
                order_by="created_at"
            )
            
            return [self._dict_to_entity(user_data) for user_data in users_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find active users: {e}")
            return []
    
    def find_users_by_status(self, status: UserStatus, limit: int = 50) -> List[User]:
        """
        Find users by online status
        
        Args:
            status: User status to filter by
            limit: Maximum number of users to return
            
        Returns:
            List of user entities with the specified status
        """
        try:
            users_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    ("is_active", "==", True),
                    ("status", "==", status.value)
                ],
                limit=limit
            )
            
            return [self._dict_to_entity(user_data) for user_data in users_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find users by status {status}: {e}")
            return []
    
    def _entity_to_dict(self, user: User) -> dict:
        """
        Convert user entity to dictionary for Firestore
        
        Args:
            user: User entity
            
        Returns:
            Dictionary representation
        """
        return {
            "id": str(user.id),
            "display_name": user.display_name,
            "email": user.email.lower() if user.email else None,  # Store email in lowercase
            "phone_number": user.phone_number,
            "firebase_uid": user.firebase_uid,  # Firebase Auth UID
            "password_hash": user.password_hash,
            "push_token": user.push_token,
            "status": user.status.value,
            "last_seen": user.last_seen.isoformat(),
            "created_at": user.created_at.isoformat(),
            "is_active": user.is_active,
            "profile_image_url": user.profile_image_url,
            "bio": user.bio,
            "preferred_language": user.preferred_language,
            "topic_preferences": user.topic_preferences,
            "interest_levels": user.interest_levels,
            "ai_enabled": user.ai_enabled,
        }
    
    def _dict_to_entity(self, data: dict) -> User:
        """
        Convert dictionary to user entity
        
        Args:
            data: Dictionary from Firestore
            
        Returns:
            User entity
        """
        from datetime import datetime
        
        return User(
            id=UUID(data["id"]),
            display_name=data["display_name"],
            email=data.get("email"),
            phone_number=data.get("phone_number"),
            firebase_uid=data["firebase_uid"],  # Firebase Auth UID
            password_hash=data["password_hash"],
            push_token=data.get("push_token"),
            status=UserStatus(data.get("status", UserStatus.OFFLINE.value)),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            is_active=data.get("is_active", True),
            profile_image_url=data.get("profile_image_url"),
            bio=data.get("bio"),
            preferred_language=data.get("preferred_language", "en"),
            topic_preferences=data.get("topic_preferences", []),
            interest_levels=data.get("interest_levels", {}),
            ai_enabled=data.get("ai_enabled", False),
        ) 