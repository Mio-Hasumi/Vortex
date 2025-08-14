"""
Manage Topic Preferences Use Case
"""

import logging
from typing import List, Optional
from uuid import UUID

from domain.entities import User, Topic
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.topic_repository import TopicRepository

logger = logging.getLogger(__name__)


class ManageTopicPreferencesUseCase:
    """
    Use case for managing user topic preferences
    """
    
    def __init__(self, user_repository: UserRepository, topic_repository: TopicRepository):
        self.user_repository = user_repository
        self.topic_repository = topic_repository
    
    def get_user_preferences(self, user_id: UUID) -> List[Topic]:
        """
        Get user's topic preferences
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of preferred topics
        """
        try:
            logger.info(f"🔍 Getting topic preferences for user: {user_id}")
            
            user = self.user_repository.find_by_id(user_id)
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return []
            
            # Get full topic objects for user's interests
            preferred_topics = []
            for topic_id in user.interests:
                topic = self.topic_repository.find_by_id(UUID(topic_id))
                if topic:
                    preferred_topics.append(topic)
            
            logger.info(f"✅ Retrieved {len(preferred_topics)} topic preferences")
            return preferred_topics
            
        except Exception as e:
            logger.error(f"❌ Failed to get topic preferences for {user_id}: {e}")
            raise
    
    def set_user_preferences(self, user_id: UUID, topic_ids: List[UUID]) -> bool:
        """
        Set user's topic preferences
        
        Args:
            user_id: User's UUID
            topic_ids: List of topic IDs to set as preferences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔧 Setting topic preferences for user: {user_id}")
            
            user = self.user_repository.find_by_id(user_id)
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return False
            
            # Validate that all topics exist
            valid_topic_ids = []
            for topic_id in topic_ids:
                topic = self.topic_repository.find_by_id(topic_id)
                if topic and topic.is_active:
                    valid_topic_ids.append(str(topic_id))
                else:
                    logger.warning(f"⚠️ Invalid or inactive topic: {topic_id}")
            
            # Update user interests
            user.interests = valid_topic_ids
            
            # Update timestamps
            from datetime import datetime
            user.updated_at = datetime.utcnow()
            
            # Save updated user
            self.user_repository.update(user)
            
            logger.info(f"✅ Topic preferences updated: {len(valid_topic_ids)} topics")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set topic preferences for {user_id}: {e}")
            raise
    
    def add_topic_preference(self, user_id: UUID, topic_id: UUID) -> bool:
        """
        Add a single topic to user's preferences
        
        Args:
            user_id: User's UUID
            topic_id: Topic ID to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"➕ Adding topic preference for user: {user_id}")
            
            user = self.user_repository.find_by_id(user_id)
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return False
            
            # Check if topic exists and is active
            topic = self.topic_repository.find_by_id(topic_id)
            if not topic or not topic.is_active:
                logger.warning(f"⚠️ Invalid or inactive topic: {topic_id}")
                return False
            
            # Add to interests if not already present
            topic_str = str(topic_id)
            if topic_str not in user.interests:
                user.interests.append(topic_str)
                
                # Update timestamps
                from datetime import datetime
                user.updated_at = datetime.utcnow()
                
                # Save updated user
                self.user_repository.update(user)
                
                logger.info(f"✅ Topic preference added: {topic.name}")
                return True
            else:
                logger.info(f"⏩ Topic already in preferences: {topic.name}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add topic preference for {user_id}: {e}")
            raise
    
    def remove_topic_preference(self, user_id: UUID, topic_id: UUID) -> bool:
        """
        Remove a topic from user's preferences
        
        Args:
            user_id: User's UUID
            topic_id: Topic ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"➖ Removing topic preference for user: {user_id}")
            
            user = self.user_repository.find_by_id(user_id)
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return False
            
            # Remove from interests if present
            topic_str = str(topic_id)
            if topic_str in user.interests:
                user.interests.remove(topic_str)
                
                # Update timestamps
                from datetime import datetime
                user.updated_at = datetime.utcnow()
                
                # Save updated user
                self.user_repository.update(user)
                
                logger.info(f"✅ Topic preference removed: {topic_id}")
                return True
            else:
                logger.info(f"⏩ Topic not in preferences: {topic_id}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove topic preference for {user_id}: {e}")
            raise 