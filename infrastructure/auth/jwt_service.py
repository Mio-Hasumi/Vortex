"""
JWT Service for token management
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from infrastructure.config import settings

logger = logging.getLogger(__name__)


class JWTService:
    """
    JWT token management service
    """
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_time = settings.JWT_EXPIRATION_TIME
        
    def create_access_token(self, user_id: UUID, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new access token
        
        Args:
            user_id: User's UUID
            additional_claims: Additional claims to include in token
            
        Returns:
            JWT token string
        """
        try:
            # Token expiration time
            expire = datetime.now(timezone.utc) + timedelta(seconds=self.expiration_time)
            
            # Base claims
            to_encode = {
                "sub": str(user_id),
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": "access"
            }
            
            # Add additional claims if provided
            if additional_claims:
                to_encode.update(additional_claims)
            
            # Encode token
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"✅ Created access token for user: {user_id}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ Failed to create access token: {e}")
            raise

    def create_refresh_token(self, user_id: UUID) -> str:
        """
        Create a new refresh token
        
        Args:
            user_id: User's UUID
            
        Returns:
            JWT refresh token string
        """
        try:
            # Refresh token expires in 7 days
            expire = datetime.now(timezone.utc) + timedelta(days=7)
            
            to_encode = {
                "sub": str(user_id),
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": "refresh"
            }
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"✅ Created refresh token for user: {user_id}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ Failed to create refresh token: {e}")
            raise

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                raise JWTError("Invalid token type")
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                raise JWTError("Token has no expiration")
            
            if datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                raise JWTError("Token has expired")
            
            logger.debug(f"✅ Token verified for user: {payload.get('sub')}")
            return payload
            
        except JWTError as e:
            logger.warning(f"❌ Token verification failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error during token verification: {e}")
            raise JWTError("Token verification failed")

    def get_user_id_from_token(self, token: str) -> UUID:
        """
        Extract user ID from token
        
        Args:
            token: JWT token string
            
        Returns:
            User's UUID
        """
        try:
            payload = self.verify_token(token)
            user_id_str = payload.get("sub")
            
            if not user_id_str:
                raise JWTError("Token has no subject")
            
            return UUID(user_id_str)
            
        except (JWTError, ValueError) as e:
            logger.warning(f"❌ Failed to extract user ID from token: {e}")
            raise JWTError("Invalid token")

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create new access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
        """
        try:
            payload = self.verify_token(refresh_token)
            
            # Ensure this is a refresh token
            if payload.get("type") != "refresh":
                raise JWTError("Invalid token type for refresh")
            
            user_id = UUID(payload.get("sub"))
            
            # Create new access token
            return self.create_access_token(user_id)
            
        except (JWTError, ValueError) as e:
            logger.warning(f"❌ Failed to refresh access token: {e}")
            raise JWTError("Invalid refresh token")

    def revoke_token(self, token: str) -> None:
        """
        Revoke a token (add to blacklist)
        
        Note: This is a placeholder implementation.
        In production, you should implement token blacklisting using Redis or database.
        
        Args:
            token: JWT token to revoke
        """
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            # TODO: Implement token blacklisting
            # For now, just log the revocation
            logger.info(f"✅ Token revoked for user: {user_id}")
            
        except JWTError as e:
            logger.warning(f"❌ Failed to revoke token: {e}")
            raise

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted
        
        Note: This is a placeholder implementation.
        In production, you should implement token blacklisting using Redis or database.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        # TODO: Implement token blacklisting check
        # For now, always return False
        return False

    def get_token_expiration(self, token: str) -> datetime:
        """
        Get token expiration time
        
        Args:
            token: JWT token string
            
        Returns:
            Token expiration datetime
        """
        try:
            payload = self.verify_token(token)
            exp = payload.get("exp")
            
            if exp is None:
                raise JWTError("Token has no expiration")
            
            return datetime.fromtimestamp(exp, timezone.utc)
            
        except JWTError as e:
            logger.warning(f"❌ Failed to get token expiration: {e}")
            raise

    def decode_token_without_verification(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging purposes)
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"❌ Failed to decode token: {e}")
            raise 