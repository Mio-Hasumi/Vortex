"""
VortexAgent Management API

Optional endpoints for managing AI agents in rooms.
These are mainly for advanced features and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import User

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class AgentStatusResponse(BaseModel):
    room_id: str
    room_name: str
    agent_identity: str
    is_active: bool
    deployment_time: str
    participants_count: int
    ai_features: List[str]

class AgentSettingsRequest(BaseModel):
    personality: Optional[str] = "friendly"  # friendly, professional, casual
    engagement_level: Optional[int] = 8      # 1-10 scale
    greeting_enabled: Optional[bool] = True
    fact_checking_enabled: Optional[bool] = True
    topic_suggestions_enabled: Optional[bool] = True

class AgentSettingsResponse(BaseModel):
    success: bool
    message: str
    updated_settings: Dict[str, Any]

class AgentStatsResponse(BaseModel):
    total_agents: int
    active_agents: int
    rooms_with_agents: List[str]
    timestamp: str

# Dependency injection
def get_agent_manager_service():
    return container.get_agent_manager_service()

def get_room_repository():
    return container.get_room_repository()

# Agent Management Endpoints

@router.get("/status/{room_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    room_id: str,
    agent_manager = Depends(get_agent_manager_service),
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get VortexAgent status for a specific room
    
    Returns information about whether an AI agent is active in the room,
    its current settings, and available features.
    """
    try:
        # Verify room exists and user has access
        room_uuid = UUID(room_id)
        room = room_repo.find_by_id(room_uuid)
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Check if user is a participant (optional security check)
        if current_user.id not in room.current_participants:
            logger.warning(f"User {current_user.id} accessing agent status for room they're not in: {room_id}")
            # Could enforce this, but being permissive for now
        
        if not agent_manager:
            return AgentStatusResponse(
                room_id=room_id,
                room_name=room.name,
                agent_identity="none",
                is_active=False,
                deployment_time="",
                participants_count=len(room.current_participants),
                ai_features=[]
            )
        
        # Get agent info
        agent_info = agent_manager.get_agent_info(room.livekit_room_name)
        
        if not agent_info or agent_info.get("status") != "active":
            return AgentStatusResponse(
                room_id=room_id,
                room_name=room.name,
                agent_identity="none",
                is_active=False,
                deployment_time="",
                participants_count=len(room.current_participants),
                ai_features=[]
            )
        
        return AgentStatusResponse(
            room_id=room_id,
            room_name=room.name,
            agent_identity=agent_info.get("agent_identity", ""),
            is_active=True,
            deployment_time=agent_info.get("deployment_time", "").isoformat() if isinstance(agent_info.get("deployment_time"), object) else str(agent_info.get("deployment_time", "")),
            participants_count=len(room.current_participants),
            ai_features=[
                "conversation_hosting",
                "topic_suggestions", 
                "fact_checking",
                "participation_encouragement",
                "smooth_transitions"
            ]
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Error getting agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )

@router.put("/settings/{room_id}", response_model=AgentSettingsResponse)
async def update_agent_settings(
    room_id: str,
    settings: AgentSettingsRequest,
    agent_manager = Depends(get_agent_manager_service),
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Update VortexAgent settings for a specific room
    
    Allows room participants to customize the AI agent's behavior,
    personality, and feature settings.
    """
    try:
        # Verify room exists and user has access
        room_uuid = UUID(room_id)
        room = room_repo.find_by_id(room_uuid)
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Check if user is a participant (enforce for settings changes)
        if current_user.id not in room.current_participants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a room participant to change agent settings"
            )
        
        if not agent_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent manager service not available"
            )
        
        # Prepare settings dictionary
        new_settings = {}
        if settings.personality is not None:
            new_settings["personality"] = settings.personality
        if settings.engagement_level is not None:
            new_settings["engagement_level"] = max(1, min(10, settings.engagement_level))
        if settings.greeting_enabled is not None:
            new_settings["greeting_enabled"] = settings.greeting_enabled
        if settings.fact_checking_enabled is not None:
            new_settings["fact_checking_enabled"] = settings.fact_checking_enabled
        if settings.topic_suggestions_enabled is not None:
            new_settings["topic_suggestions_enabled"] = settings.topic_suggestions_enabled
        
        # Update agent settings
        result = await agent_manager.update_agent_settings(
            room_name=room.livekit_room_name,
            settings=new_settings
        )
        
        if result.get("success"):
            return AgentSettingsResponse(
                success=True,
                message="Agent settings updated successfully",
                updated_settings=new_settings
            )
        else:
            return AgentSettingsResponse(
                success=False,
                message=result.get("error", "Failed to update settings"),
                updated_settings={}
            )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating agent settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent settings"
        )

@router.delete("/{room_id}")
async def remove_agent_from_room(
    room_id: str,
    agent_manager = Depends(get_agent_manager_service),
    room_repo = Depends(get_room_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Remove VortexAgent from a specific room
    
    This is mainly for administrative purposes or if users want
    to have a conversation without AI assistance.
    """
    try:
        # Verify room exists and user has access
        room_uuid = UUID(room_id)
        room = room_repo.find_by_id(room_uuid)
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Check if user is room creator or participant
        if current_user.id != room.created_by and current_user.id not in room.current_participants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room creator or participants can remove the agent"
            )
        
        if not agent_manager:
            return {"success": True, "message": "No agent manager service available"}
        
        # Remove agent from room
        result = await agent_manager.remove_agent_from_room(room.livekit_room_name)
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "Agent removal completed"),
            "removed_at": result.get("stopped_at", "")
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error removing agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove agent"
        )

@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    agent_manager = Depends(get_agent_manager_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall VortexAgent deployment statistics
    
    Useful for monitoring and debugging purposes.
    This endpoint could be restricted to admin users in production.
    """
    try:
        if not agent_manager:
            return AgentStatsResponse(
                total_agents=0,
                active_agents=0,
                rooms_with_agents=[],
                timestamp=""
            )
        
        stats = agent_manager.get_agent_stats()
        
        return AgentStatsResponse(
            total_agents=stats.get("total_agents", 0),
            active_agents=stats.get("active_agents", 0),
            rooms_with_agents=stats.get("rooms_with_agents", []),
            timestamp=stats.get("timestamp", "")
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting agent stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent statistics"
        ) 