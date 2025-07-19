"""
Topics API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import User
from usecase.manage_topic_preferences import ManageTopicPreferencesUseCase

router = APIRouter()

# Request/Response Models
class TopicResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    difficulty_level: int
    is_active: bool

class TopicListResponse(BaseModel):
    topics: List[TopicResponse]
    total: int

class UserTopicPreference(BaseModel):
    topic_id: str
    interest_level: int  # 1-5 scale

class UserTopicPreferencesRequest(BaseModel):
    topic_ids: List[str]

# Dependency injection
def get_topic_repository():
    return container.get_topic_repository()

def get_user_repository():
    return container.get_user_repository()

def get_manage_topic_preferences_usecase():
    """Get manage topic preferences use case"""
    return ManageTopicPreferencesUseCase(
        user_repository=get_user_repository(),
        topic_repository=get_topic_repository()
    )

# Topics endpoints
@router.get("/", response_model=TopicListResponse)
async def get_topics(
    category: Optional[str] = None,
    difficulty_level: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    topic_repo = Depends(get_topic_repository)
):
    """
    Get available topics for matching
    """
    try:
        if category:
            topics = topic_repo.find_by_category(category, limit)
        elif difficulty_level:
            topics = topic_repo.find_by_difficulty_level(difficulty_level, limit)
        else:
            topics = topic_repo.get_all_topics(limit)

        topic_responses = []
        for topic in topics:
            topic_responses.append(TopicResponse(
                id=str(topic.id),
                name=topic.name,
                description=topic.description,
                category=topic.category,
                difficulty_level=topic.difficulty_level,
                is_active=topic.is_active
            ))

        return TopicListResponse(
            topics=topic_responses,
            total=len(topic_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: str, topic_repo = Depends(get_topic_repository)):
    """
    Get specific topic details
    """
    try:
        topic_uuid = UUID(topic_id)
        topic = topic_repo.find_by_id(topic_uuid)
        
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )

        return TopicResponse(
            id=str(topic.id),
            name=topic.name,
            description=topic.description,
            category=topic.category,
            difficulty_level=topic.difficulty_level,
            is_active=topic.is_active
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid topic ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/preferences")
async def set_topic_preferences(
    request: UserTopicPreferencesRequest,
    current_user: User = Depends(get_current_user),
    usecase = Depends(get_manage_topic_preferences_usecase)
):
    """
    Set user's topic preferences for matching
    """
    try:
        current_user_id = current_user.id
        
        # Convert string IDs to UUIDs
        topic_uuids = []
        for topic_id in request.topic_ids:
            try:
                topic_uuids.append(UUID(topic_id))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid topic ID format: {topic_id}"
                )
        
        # Set user preferences using the use case
        success = usecase.set_user_preferences(current_user_id, topic_uuids)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update topic preferences"
            )
        
        return {"message": "Preferences updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/preferences")
async def get_topic_preferences(
    current_user: User = Depends(get_current_user),
    usecase = Depends(get_manage_topic_preferences_usecase)
):
    """
    Get current user's topic preferences
    """
    try:
        current_user_id = current_user.id
        
        # Get user preferences using the use case
        preferred_topics = usecase.get_user_preferences(current_user_id)
        
        preferences = []
        for topic in preferred_topics:
            preferences.append(UserTopicPreference(
                topic_id=str(topic.id),
                interest_level=5  # Default interest level - could be enhanced later
            ))
        
        return {
            "preferences": preferences,
            "total": len(preferences)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 