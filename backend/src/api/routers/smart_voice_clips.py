"""
Smart Voice Clips API routes
Handles smart voice clips created from hashtag mentions in chat rooms
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import io

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import User, SmartVoiceClip

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response Models
class SmartVoiceClipResponse(BaseModel):
    id: str
    room_id: str
    hashtag: str
    start_time_ms: int
    end_time_ms: int
    duration_ms: int
    transcription: str
    confidence: float
    created_at: str
    download_url: Optional[str] = None
    time_range_string: str

class SmartVoiceClipSummary(BaseModel):
    total_clips: int
    hashtags: List[str]
    total_duration_seconds: float
    clips_by_hashtag: dict

class SmartVoiceClipListResponse(BaseModel):
    clips: List[SmartVoiceClipResponse]
    summary: SmartVoiceClipSummary
    total: int

# Dependency injection
def get_smart_voice_clipping_service():
    return container.get_smart_voice_clipping_service()

def get_smart_voice_clip_repository():
    return container.get_smart_voice_clip_repository()

# Smart Voice Clips endpoints
@router.get("/rooms/{room_id}/clips", response_model=SmartVoiceClipListResponse)
async def get_room_smart_clips(
    room_id: str,
    hashtag: Optional[str] = Query(None, description="Filter by specific hashtag"),
    limit: int = Query(50, description="Maximum number of clips to return"),
    offset: int = Query(0, description="Number of clips to skip"),
    current_user: User = Depends(get_current_user)
):
    """
    Get smart voice clips for a chat room
    """
    try:
        room_uuid = UUID(room_id)
        clipping_service = get_smart_voice_clipping_service()
        
        if not clipping_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Smart voice clipping service not available"
            )
        
        # Get clips
        clips = await clipping_service.get_room_clips(room_uuid, hashtag)
        
        # Apply pagination
        total_clips = len(clips)
        clips = clips[offset:offset + limit] if limit else clips
        
        # Convert to response format
        clip_responses = []
        for clip in clips:
            clip_responses.append(SmartVoiceClipResponse(
                id=str(clip.id),
                room_id=str(clip.room_id),
                hashtag=clip.hashtag,
                start_time_ms=clip.start_time_ms,
                end_time_ms=clip.end_time_ms,
                duration_ms=clip.duration_ms,
                transcription=clip.transcription,
                confidence=clip.confidence,
                created_at=clip.created_at.isoformat(),
                download_url=clip.download_url,
                time_range_string=clip.get_time_range_string()
            ))
        
        # Get summary
        summary_data = await clipping_service.get_room_clips_summary(room_uuid)
        summary = SmartVoiceClipSummary(**summary_data)
        
        return SmartVoiceClipListResponse(
            clips=clip_responses,
            summary=summary,
            total=total_clips
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Failed to get smart clips for room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get smart clips: {str(e)}"
        )

@router.get("/rooms/{room_id}/clips/{clip_id}/download")
async def download_smart_clip(
    room_id: str,
    clip_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download a specific smart voice clip
    """
    try:
        room_uuid = UUID(room_id)
        clip_uuid = UUID(clip_id)
        
        clip_repo = get_smart_voice_clip_repository()
        clip = clip_repo.find_by_id(clip_uuid)
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Smart voice clip not found"
            )
        
        # Check if clip belongs to the room
        if clip.room_id != room_uuid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Smart voice clip not found in this room"
            )
        
        # Return audio data as streaming response
        def generate_audio():
            yield clip.audio_data
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=clip_{clip_id}_{clip.hashtag.replace('#', '')}.wav",
                "Content-Length": str(len(clip.audio_data))
            }
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID or clip ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download smart clip {clip_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download smart clip: {str(e)}"
        )

@router.get("/rooms/{room_id}/clips/summary", response_model=SmartVoiceClipSummary)
async def get_room_clips_summary(
    room_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of smart voice clips for a room
    """
    try:
        room_uuid = UUID(room_id)
        clipping_service = get_smart_voice_clipping_service()
        
        if not clipping_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Smart voice clipping service not available"
            )
        
        summary_data = await clipping_service.get_room_clips_summary(room_uuid)
        return SmartVoiceClipSummary(**summary_data)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Failed to get clips summary for room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clips summary: {str(e)}"
        )

@router.post("/rooms/{room_id}/clips/start-recording")
async def start_room_recording(
    room_id: str,
    hashtags: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    Start smart voice recording for a chat room
    """
    try:
        room_uuid = UUID(room_id)
        clipping_service = get_smart_voice_clipping_service()
        
        if not clipping_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Smart voice clipping service not available"
            )
        
        success = await clipping_service.start_room_recording(room_uuid, hashtags)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to start recording. Room may already be recording."
            )
        
        return {
            "message": "Smart voice recording started successfully",
            "room_id": room_id,
            "hashtags": hashtags
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Failed to start recording for room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recording: {str(e)}"
        )

@router.post("/rooms/{room_id}/clips/stop-recording")
async def stop_room_recording(
    room_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stop smart voice recording for a chat room
    """
    try:
        room_uuid = UUID(room_id)
        clipping_service = get_smart_voice_clipping_service()
        
        if not clipping_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Smart voice clipping service not available"
            )
        
        summary = await clipping_service.stop_room_recording(room_uuid)
        
        return {
            "message": "Smart voice recording stopped successfully",
            "room_id": room_id,
            "summary": summary
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Failed to stop recording for room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop recording: {str(e)}"
        )

@router.delete("/rooms/{room_id}/clips")
async def delete_room_clips(
    room_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete all smart voice clips for a room
    """
    try:
        room_uuid = UUID(room_id)
        clip_repo = get_smart_voice_clip_repository()
        
        deleted_count = clip_repo.delete_by_room(room_uuid)
        
        return {
            "message": f"Deleted {deleted_count} smart voice clips",
            "room_id": room_id,
            "deleted_count": deleted_count
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    except Exception as e:
        logger.error(f"❌ Failed to delete clips for room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete clips: {str(e)}"
        )
