"""
Firebase Authentication Middleware for FastAPI

"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth

from domain.entities import User
from infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer()


class FirebaseAuthMiddleware:
    """
    Firebase Authentication Middleware
    Use Firebase ID Token for user authentication, replacing custom JWT
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security), test_mode: bool = False) -> User:
        """
        Get current authenticated user from Firebase ID Token
        
        Args:
            credentials: HTTP authorization credentials
            test_mode: Whether in test mode
            
        Returns:
            Current authenticated user
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Get Firebase ID Token
            token = credentials.credentials
            
            # Test mode: Extract test user ID from token
            if test_mode and token.startswith("test_token_"):
                firebase_uid = token.replace("test_token_", "")
            else:
                # Normal mode: Verify Firebase ID Token
                decoded_token = auth.verify_id_token(token)
                firebase_uid = decoded_token['uid']
            
            # Find user by Firebase UID
            user = self.user_repository.find_by_firebase_uid(firebase_uid)
            
            if not user:
                logger.warning(f"User not found for Firebase UID: {firebase_uid}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                logger.warning(f"Inactive user attempted access: {user.id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is deactivated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.info(f"User authenticated successfully: {user.id}")
            return user
            
        except auth.InvalidIdTokenError:
            logger.error("Invalid Firebase ID Token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.ExpiredIdTokenError:
            logger.error("Expired Firebase ID Token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.RevokedIdTokenError:
            logger.error("Revoked Firebase ID Token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_current_user_optional(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
        """
        Get current user (optional)
        Returns None instead of raising exception if token is invalid
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Current user or None
        """
        try:
            return self.get_current_user(credentials)
        except HTTPException:
            return None
    
    def verify_firebase_token(self, token: str) -> dict:
        """
        验证Firebase ID Token并返回解码后的信息
        
        Args:
            token: Firebase ID Token
            
        Returns:
            解码后的token信息
            
        Raises:
            HTTPException: 如果token无效
        """
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token
            
        except auth.InvalidIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
            )
        except auth.RevokedIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has been revoked",
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )


# 创建全局实例，避免循环依赖
firebase_auth_instance = None

def get_firebase_auth_middleware():
    """获取Firebase认证中间件实例"""
    global firebase_auth_instance
    if firebase_auth_instance is None:
        from infrastructure.container import container
        from infrastructure.repositories.user_repository import UserRepository
        from infrastructure.db.firebase import FirebaseAdminService
        
        # 创建用户仓库
        db = FirebaseAdminService()
        user_repo = UserRepository(db)
        firebase_auth_instance = FirebaseAuthMiddleware(user_repo)
    
    return firebase_auth_instance

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    获取当前认证用户的依赖函数
    替代原来的JWT认证
    """
    # 检查是否为测试token
    token = credentials.credentials
    test_mode = token.startswith("test_token_")
    
    # 直接获取认证中间件实例
    firebase_auth = get_firebase_auth_middleware()
    
    return firebase_auth.get_current_user(credentials, test_mode=test_mode)