"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from domain.entities import User
from usecase.sign_in import SignInInteractor, SignInInput, SignInOutput
from usecase.sign_up import SignUpInteractor, SignUpInput, SignUpOutput
from usecase.sign_out import SignOutInteractor
from infrastructure.container import container

router = APIRouter()
security = HTTPBearer()

# Request/Response Models
class SignUpRequest(BaseModel):
    display_name: str
    email: str
    password: str

class SignInRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    display_name: str
    email: str

# Dependency injection
def get_sign_up_interactor():
    return container.get_sign_up_interactor()

def get_sign_in_interactor():
    return container.get_sign_in_interactor()

def get_jwt_service():
    return container.get_jwt_service()

def get_current_user_from_token(token: str):
    jwt_service = container.get_jwt_service()
    user_repo = container.get_user_repository()
    
    try:
        user_id = jwt_service.get_user_id_from_token(token)
        user = user_repo.find_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Authentication endpoints
@router.post("/signup", response_model=AuthResponse)
async def sign_up(
    request: SignUpRequest,
    interactor: SignUpInteractor = Depends(get_sign_up_interactor)
):
    """
    Register a new user
    """
    try:
        input_data = SignUpInput(
            display_name=request.display_name,
            email=request.email,
            password=request.password
        )
        
        result = interactor.execute(input_data)
        
        return AuthResponse(
            user_id=str(result.user_id),
            access_token=result.access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/signin", response_model=AuthResponse)
async def sign_in(
    request: SignInRequest,
    interactor: SignInInteractor = Depends(get_sign_in_interactor)
):
    """
    Sign in an existing user
    """
    try:
        input_data = SignInInput(
            email=request.email,
            password=request.password
        )
        
        result = interactor.execute(input_data)
        
        return AuthResponse(
            user_id=str(result.user_id),
            access_token=result.access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/signout")
async def sign_out(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_service = Depends(get_jwt_service)
):
    """
    Sign out current user
    """
    try:
        # Revoke the token
        jwt_service.revoke_token(credentials.credentials)
        return {"message": "Successfully signed out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current user profile
    """
    try:
        user = get_current_user_from_token(credentials.credentials)
        
        return UserResponse(
            id=str(user.id),
            display_name=user.display_name,
            email=user.email
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    updates: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update current user profile
    """
    try:
        user = get_current_user_from_token(credentials.credentials)
        
        # Get the update profile use case
        from infrastructure.container import container
        update_use_case = container.update_user_profile_use_case
        
        # Execute update
        updated_user = update_use_case.execute(user.id, updates)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(updated_user.id),
            display_name=updated_user.display_name,
            email=updated_user.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.get("/me/preferences")
async def get_user_topic_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current user's topic preferences
    """
    try:
        user = get_current_user_from_token(credentials.credentials)
        
        # Get the topic preferences use case
        from infrastructure.container import container
        preferences_use_case = container.manage_topic_preferences_use_case
        
        # Get preferences
        preferences = preferences_use_case.get_user_preferences(user.id)
        
        return {
            "topics": [
                {
                    "id": str(topic.id),
                    "name": topic.name,
                    "description": topic.description,
                    "category": topic.category,
                    "difficulty_level": topic.difficulty_level
                }
                for topic in preferences
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences"
        )

@router.put("/me/preferences")
async def update_user_topic_preferences(
    preferences: Dict[str, List[str]],
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update current user's topic preferences
    """
    try:
        user = get_current_user_from_token(credentials.credentials)
        
        # Get the topic preferences use case
        from infrastructure.container import container
        preferences_use_case = container.manage_topic_preferences_use_case
        
        # Parse topic IDs
        from uuid import UUID
        topic_ids = [UUID(topic_id) for topic_id in preferences.get("topic_ids", [])]
        
        # Update preferences
        success = preferences_use_case.set_user_preferences(user.id, topic_ids)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update preferences"
            )
        
        return {"message": "Preferences updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        ) 