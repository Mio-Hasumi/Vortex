"""
Get User Profile Use Case
"""

import logging
from typing import Optional
from uuid import UUID

from domain.entities import User
from infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class GetUserProfileUseCase:
    """
    Use case for getting user profile information
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def execute(self, user_id: UUID) -> Optional[User]:
        """
        Get user profile by ID
        
        Args:
            user_id: User's UUID
            
        Returns:
            User entity or None if not found
        """
        try:
            logger.info(f"🔍 Getting user profile for: {user_id}")
            
            # Find user by ID
            user = self.user_repository.find_by_id(user_id)
            
            if not user:
                logger.warning(f"⚠️ User not found: {user_id}")
                return None
            
            logger.info(f"✅ User profile retrieved successfully: {user.display_name}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Failed to get user profile {user_id}: {e}")
            raise 