"""
Authentication API routes - Pure Firebase Authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from domain.entities import User
from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user

router = APIRouter()
security = HTTPBearer()

# Request/Response Models
class SignUpRequest(BaseModel):
    firebase_uid: str  # Firebase UID from client
    display_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None

class SignInRequest(BaseModel):
    firebase_uid: str  # Firebase UID from client
    email: Optional[str] = None
    phone_number: Optional[str] = None

class AuthResponse(BaseModel):
    user_id: str
    display_name: str
    email: str
    message: str

class UserResponse(BaseModel):
    id: str
    display_name: str
    email: str

# Dependency injection
def get_user_repository():
    return container.get_user_repository()

# Authentication endpoints
@router.post("/register", response_model=AuthResponse)
async def sign_up(
    request: SignUpRequest,
    user_repo = Depends(get_user_repository)
):
    """
    Register a new user (Firebase user already created on client)
    Client should create Firebase user first, then call this endpoint
    """
    try:
        # Validate that either email or phone_number is provided
        if not request.email and not request.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either email or phone_number must be provided"
            )
        
        # Check if user already exists by email
        if request.email:
            existing_user = user_repo.find_by_email(request.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
        
        # Check if user already exists by phone number
        if request.phone_number:
            existing_user = user_repo.find_by_phone_number(request.phone_number)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this phone number already exists"
                )
        
        existing_user_by_name = user_repo.find_by_display_name(request.display_name)
        if existing_user_by_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this display name already exists"
            )
        
        # Create user in our database
        from domain.entities import new_user
        user = new_user(
            display_name=request.display_name,
            email=request.email,
            phone_number=request.phone_number,
            firebase_uid=request.firebase_uid,
            password_hash=""  # Not needed for Firebase auth
        )
        
        saved_user = user_repo.save(user)
        
        return AuthResponse(
            user_id=str(saved_user.id),
            display_name=saved_user.display_name,
            email=saved_user.email or "",
            message="User registered successfully. Use Firebase ID Token for authentication."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=AuthResponse)
async def sign_in(
    request: SignInRequest,
    user_repo = Depends(get_user_repository)
):
    """
    Sign in user (Firebase authentication handled on client)
    This endpoint just verifies the user exists in our database
    """
    try:
        # Find user by Firebase UID
        user = user_repo.find_by_firebase_uid(request.firebase_uid)
        if not user:
            # If user doesn't exist, try to find by email or phone
            if request.email:
                user = user_repo.find_by_email(request.email)
            elif request.phone_number:
                user = user_repo.find_by_phone_number(request.phone_number)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found. Please sign up first."
                )
        
        return AuthResponse(
            user_id=str(user.id),
            display_name=user.display_name,
            email=user.email or "",
            message="User authenticated successfully. Use Firebase ID Token for API calls."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/signout")
async def sign_out():
    """
    Sign out (handled on client with Firebase Auth)
    """
    return {"message": "Please sign out using Firebase Auth SDK on client"}

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile (requires Firebase ID Token)
    """
    return UserResponse(
        id=str(current_user.id),
        display_name=current_user.display_name,
        email=current_user.email
        ) 