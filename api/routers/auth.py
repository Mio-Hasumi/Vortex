"""
Authentication API routes - Pure Firebase Authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import os
import uuid
from datetime import datetime

from domain.entities import User
from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from infrastructure.config import Settings

# Get settings instance
settings = Settings()

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
    email: Optional[str] = None
    message: str

class UserResponse(BaseModel):
    id: str
    display_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None

class UpdateDisplayNameRequest(BaseModel):
    display_name: str

class AddAuthMethodRequest(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None

class UpdateProfileResponse(BaseModel):
    message: str
    user: UserResponse

class ProfilePictureResponse(BaseModel):
    message: str
    profile_image_url: str
    user: UserResponse

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
    try:
        # Ensure profile_image_url is a full URL
        profile_image_url = current_user.profile_image_url
        if profile_image_url and profile_image_url.startswith("/"):
            profile_image_url = f"{settings.BASE_URL}{profile_image_url}"
        
        # Log the user data being returned for debugging
        logger.info(f"🔍 [Profile] Returning profile for user: {current_user.id} ({current_user.display_name})")
        logger.info(f"🔍 [Profile] Email: {current_user.email}, Phone: {current_user.phone_number}")
        
        return UserResponse(
            id=str(current_user.id),
            display_name=current_user.display_name,
            email=current_user.email,
            phone_number=current_user.phone_number,
            profile_image_url=profile_image_url
        )
    except Exception as e:
        logger.error(f"❌ [Profile] Error getting profile for user {current_user.id}: {e}")
        logger.error(f"❌ [Profile] User data: {current_user}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )

@router.put("/profile/display-name", response_model=UpdateProfileResponse)
async def update_display_name(
    request: UpdateDisplayNameRequest,
    current_user: User = Depends(get_current_user),
    user_repo = Depends(get_user_repository)
):
    """
    Update user display name (requires Firebase ID Token)
    """
    try:
        # Check if display name is already taken by another user
        existing_user = user_repo.find_by_display_name(request.display_name)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Display name already taken"
            )
        
        # Update display name
        current_user.display_name = request.display_name
        current_user.update_profile()
        
        # Save updated user
        updated_user = user_repo.update(current_user)
        
        # Ensure profile_image_url is a full URL
        profile_image_url = updated_user.profile_image_url
        if profile_image_url and profile_image_url.startswith("/"):
            profile_image_url = f"{settings.BASE_URL}{profile_image_url}"
        
        return UpdateProfileResponse(
            message="Display name updated successfully",
            user=UserResponse(
                id=str(updated_user.id),
                display_name=updated_user.display_name,
                email=updated_user.email,
                phone_number=updated_user.phone_number,
                profile_image_url=profile_image_url
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/profile/auth-methods", response_model=UpdateProfileResponse)
async def add_auth_method(
    request: AddAuthMethodRequest,
    current_user: User = Depends(get_current_user),
    user_repo = Depends(get_user_repository)
):
    """
    Add additional authentication method to existing account (requires Firebase ID Token)
    """
    try:
        # Validate that at least one auth method is provided
        if not request.email and not request.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either email or phone_number must be provided"
            )
        
        # Check if email is already taken by another user
        if request.email:
            existing_user = user_repo.find_by_email(request.email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already associated with another account"
                )
            current_user.email = request.email
        
        # Check if phone number is already taken by another user
        if request.phone_number:
            existing_user = user_repo.find_by_phone_number(request.phone_number)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already associated with another account"
                )
            current_user.phone_number = request.phone_number
        
        # Update the profile timestamp
        current_user.update_profile()
        
        # Save updated user
        updated_user = user_repo.update(current_user)
        
        # Ensure profile_image_url is a full URL
        profile_image_url = updated_user.profile_image_url
        if profile_image_url and profile_image_url.startswith("/"):
            profile_image_url = f"{settings.BASE_URL}{profile_image_url}"
        
        return UpdateProfileResponse(
            message="Authentication method added successfully",
            user=UserResponse(
                id=str(updated_user.id),
                display_name=updated_user.display_name,
                email=updated_user.email,
                phone_number=updated_user.phone_number,
                profile_image_url=profile_image_url
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/profile/picture", response_model=ProfilePictureResponse)
async def upload_profile_picture(
    profile_picture: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_repo = Depends(get_user_repository)
):
    """
    Upload profile picture and store in Firebase user document (requires Firebase ID Token)
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
        if profile_picture.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format. Allowed: {', '.join(allowed_types)}"
            )
        
        # Check file size (max 2MB for base64 storage)
        max_size = 2 * 1024 * 1024  # 2MB
        file_content = await profile_picture.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file too large. Maximum size is 2MB for profile pictures."
            )
        
        # Convert to base64
        import base64
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Create data URL for easy display
        file_extension = profile_picture.filename.split(".")[-1] if "." in profile_picture.filename else "jpg"
        mime_type = profile_picture.content_type
        profile_image_url = f"data:{mime_type};base64,{image_base64}"
        
        # Update user profile with base64 image data
        current_user.profile_image_url = profile_image_url
        current_user.update_profile()
        
        # Save updated user to Firebase
        updated_user = user_repo.update(current_user)
        
        return ProfilePictureResponse(
            message="Profile picture uploaded successfully",
            profile_image_url=profile_image_url,
            user=UserResponse(
                id=str(updated_user.id),
                display_name=updated_user.display_name,
                email=updated_user.email,
                phone_number=updated_user.phone_number,
                profile_image_url=profile_image_url
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 