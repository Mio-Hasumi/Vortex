"""
Authentication Middleware for FastAPI
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from domain.entities import User
from infrastructure.auth.jwt_service import JWTService
from infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthenticationMiddleware:
    """
    Authentication middleware for validating JWT tokens and getting current user
    """
    
    def __init__(self, jwt_service: JWTService, user_repository: UserRepository):
        self.jwt_service = jwt_service
        self.user_repository = user_repository
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """
        Get current authenticated user from JWT token
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Current authenticated user
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            token = credentials.credentials
            
            # Verify JWT token
            payload = self.jwt_service.verify_token(token)
            
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get user ID from payload
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Find user in database
            user = self.user_repository.find_by_id(UUID(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if user is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.debug(f"✅ User authenticated: {user.display_name}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_optional_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
        """
        Get current authenticated user if token is provided (optional authentication)
        
        Args:
            credentials: Optional HTTP authorization credentials
            
        Returns:
            Current authenticated user or None
        """
        if not credentials:
            return None
        
        try:
            return self.get_current_user(credentials)
        except HTTPException:
            return None
        except Exception as e:
            logger.warning(f"⚠️ Optional authentication failed: {e}")
            return None


def get_auth_middleware() -> AuthenticationMiddleware:
    """
    Dependency injection for authentication middleware
    """
    from infrastructure.container import container
    return AuthenticationMiddleware(
        jwt_service=container.get_jwt_service(),
        user_repository=container.get_user_repository()
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_middleware: AuthenticationMiddleware = Depends(get_auth_middleware)
) -> User:
    """
    Dependency for getting current authenticated user
    """
    return auth_middleware.get_current_user(credentials)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_middleware: AuthenticationMiddleware = Depends(get_auth_middleware)
) -> Optional[User]:
    """
    Dependency for getting current authenticated user (optional)
    """
    return auth_middleware.get_optional_current_user(credentials)


# Legacy support for existing code
def get_current_user_from_token(token: str) -> User:
    """
    Legacy function for getting user from token (for backward compatibility)
    """
    from infrastructure.container import container
    
    try:
        # Verify JWT token
        payload = container.get_jwt_service().verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user ID from payload
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Find user in database
        user = container.get_user_repository().find_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        ) 