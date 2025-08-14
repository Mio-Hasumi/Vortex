"""
Firebase Authentication Service
==============================

Wrapper around Firebase Admin SDK for authentication operations
"""

import logging
from typing import Dict, Any, Optional
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


class FirebaseAuth:
    """
    Firebase Authentication service wrapper
    """
    
    def __init__(self):
        """Initialize Firebase Auth service"""
        logger.info("🔐 Firebase Auth service initialized")
    
    def verify_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify Firebase ID token
        
        Args:
            id_token: Firebase ID token to verify
            
        Returns:
            Decoded token claims
            
        Raises:
            FirebaseError: If token verification fails
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            logger.info(f"✅ Token verified for user: {decoded_token.get('uid')}")
            return decoded_token
        except FirebaseError as e:
            logger.error(f"❌ Token verification failed: {e}")
            raise
    
    def get_user(self, uid: str) -> Dict[str, Any]:
        """
        Get user by UID
        
        Args:
            uid: User UID
            
        Returns:
            User record
        """
        try:
            user_record = auth.get_user(uid)
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'display_name': user_record.display_name,
                'email_verified': user_record.email_verified,
                'disabled': user_record.disabled,
            }
        except FirebaseError as e:
            logger.error(f"❌ Failed to get user {uid}: {e}")
            raise
    
    def create_user(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            email: User email
            password: User password
            display_name: Optional display name
            
        Returns:
            Created user record
        """
        try:
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            logger.info(f"✅ User created: {user_record.uid}")
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'display_name': user_record.display_name,
            }
        except FirebaseError as e:
            logger.error(f"❌ Failed to create user: {e}")
            raise
    
    def update_user(self, uid: str, **kwargs) -> Dict[str, Any]:
        """
        Update user properties
        
        Args:
            uid: User UID
            **kwargs: Properties to update
            
        Returns:
            Updated user record
        """
        try:
            user_record = auth.update_user(uid, **kwargs)
            logger.info(f"✅ User updated: {uid}")
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'display_name': user_record.display_name,
            }
        except FirebaseError as e:
            logger.error(f"❌ Failed to update user {uid}: {e}")
            raise
    
    def delete_user(self, uid: str) -> bool:
        """
        Delete a user
        
        Args:
            uid: User UID
            
        Returns:
            True if successful
        """
        try:
            auth.delete_user(uid)
            logger.info(f"✅ User deleted: {uid}")
            return True
        except FirebaseError as e:
            logger.error(f"❌ Failed to delete user {uid}: {e}")
            raise
    
    def generate_custom_token(self, uid: str, additional_claims: Dict[str, Any] = None) -> str:
        """
        Generate custom token for user
        
        Args:
            uid: User UID
            additional_claims: Optional additional claims
            
        Returns:
            Custom token string
        """
        try:
            custom_token = auth.create_custom_token(uid, additional_claims)
            logger.info(f"✅ Custom token generated for user: {uid}")
            return custom_token.decode('utf-8')
        except FirebaseError as e:
            logger.error(f"❌ Failed to generate custom token for {uid}: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Firebase Auth service health
        
        Returns:
            Health status
        """
        try:
            # Try to list users (limit 1) to test connectivity
            page = auth.list_users(max_results=1)
            return {
                "status": "healthy",
                "service": "firebase_auth",
                "timestamp": "2025-01-19T00:00:00Z"
            }
        except Exception as e:
            logger.error(f"❌ Firebase Auth health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "firebase_auth",
                "error": str(e),
                "timestamp": "2025-01-19T00:00:00Z"
            } 