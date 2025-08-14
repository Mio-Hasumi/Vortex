"""
Update User Profile Use Case
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from domain.entities import User
from infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UpdateUserProfileUseCase:
    """
    Use case for updating user profile information
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def execute(self, user_id: UUID, updates: Dict[str, Any]) -> Optional[User]:
        """
        Update user profile
        
        Args:
            user_id: User's UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated user entity or None if not found
        """
        try:
            logger.info(f"🔧 Updating user profile for: {user_id}")
            
            # Find existing user
            user = self.user_repository.find_by_id(user_id)
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return None
            
            # Update allowed fields
            if "display_name" in updates:
                # Check if display name is available
                existing_user = self.user_repository.find_by_display_name(updates["display_name"])
                if existing_user and existing_user.id != user_id:
                    raise ValueError("Display name already taken")
                user.display_name = updates["display_name"]
            
            if "bio" in updates:
                user.bio = updates["bio"]
            
            if "interests" in updates:
                user.interests = updates["interests"]
            
            if "avatar_url" in updates:
                user.avatar_url = updates["avatar_url"]
            
            # Update timestamps
            from datetime import datetime
            user.updated_at = datetime.utcnow()
            
            # Save updated user
            updated_user = self.user_repository.update(user)
            
            logger.info(f"✅ User profile updated successfully: {user.display_name}")
            return updated_user
            
        except Exception as e:
            logger.error(f"❌ Failed to update user profile {user_id}: {e}")
            raise 