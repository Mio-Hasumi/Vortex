"""
Topics API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from infrastructure.container import container

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

# Dependency injection
def get_topic_repository():
    return container.get_topic_repository()

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
            topics = topic_repo.find_all_active(limit, offset)
        
        topic_responses = [
            TopicResponse(
                id=str(topic.id),
                name=topic.name,
                description=topic.description,
                category=topic.category,
                difficulty_level=topic.difficulty_level,
                is_active=topic.is_active
            )
            for topic in topics
        ]
        
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
        from uuid import UUID
        
        topic = topic_repo.find_by_id(UUID(topic_id))
        
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
    preferences: List[UserTopicPreference]
):
    """
    Set user's topic preferences for matching
    """
    try:
        # TODO: Implement user preference saving
        return {"message": "Preferences updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/preferences")
async def get_topic_preferences():
    """
    Get current user's topic preferences
    """
    try:
        # TODO: Implement user preference retrieval
        return {
            "preferences": [
                UserTopicPreference(topic_id="1", interest_level=5),
                UserTopicPreference(topic_id="2", interest_level=3)
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 