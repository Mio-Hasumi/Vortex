"""
Recordings API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import io

from infrastructure.container import container
from infrastructure.middleware.firebase_auth_middleware import get_current_user
from domain.entities import RecordingStatus, User

router = APIRouter()

# Request/Response Models
class RecordingResponse(BaseModel):
    id: str
    room_id: str
    room_name: str
    topic: str
    participants: List[str]
    duration: int  # seconds
    file_size: int  # bytes
    created_at: str
    status: str  # processing, ready, failed
    download_url: Optional[str] = None

class RecordingListResponse(BaseModel):
    recordings: List[RecordingResponse]
    total: int

class RecordingMetadata(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    is_public: bool = False

# Dependency injection
def get_recording_repository():
    return container.get_recording_repository()

# Recordings endpoints
@router.get("/", response_model=RecordingListResponse)
async def get_recordings(
    room_id: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's recordings
    """
    try:
        current_user_id = current_user.id
        
        # Get recordings from repository
        if room_id:
            recordings = recording_repo.find_by_room_id(UUID(room_id), limit=limit)
        elif topic:
            recordings = recording_repo.find_by_topic(topic, limit=limit)
        else:
            recordings = recording_repo.find_by_user_id(current_user_id, limit=limit)
        
        recording_responses = []
        for recording in recordings:
            recording_responses.append(RecordingResponse(
                id=str(recording.id),
                room_id=str(recording.room_id),
                room_name=recording.room_name,
                topic=recording.topic,
                participants=[str(p) for p in recording.participants],
                duration=recording.duration,
                file_size=recording.file_size,
                created_at=recording.created_at.isoformat(),
                status=recording.status.name.lower(),
                download_url=recording.download_url
            ))
        
        return RecordingListResponse(
            recordings=recording_responses,
            total=len(recording_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific recording details
    """
    try:
        recording_uuid = UUID(recording_id)
        
        # Get recording from repository
        recording = recording_repo.find_by_id(recording_uuid)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Check if user has access to this recording
        # (simplified - in production, you'd check if user was a participant)
        
        return RecordingResponse(
            id=str(recording.id),
            room_id=str(recording.room_id),
            room_name=recording.room_name or f"Room {recording.room_id}",
            topic="General",  # Could be enhanced with topic lookup
            participants=[str(p) for p in recording.participants] if recording.participants else [],
            duration=recording.duration or 0,
            file_size=recording.file_size or 0,
            created_at=recording.created_at.isoformat(),
            status=recording.status.name.lower(),
            download_url=recording.download_url
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found"
        )

@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: str,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Download recording file
    """
    try:
        recording_uuid = UUID(recording_id)
        
        # Get recording from repository
        recording = recording_repo.find_by_id(recording_uuid)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Check if recording is ready for download
        if recording.status != RecordingStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recording is not ready for download"
            )
        
        # For now, return a redirect to the download URL or placeholder
        if recording.download_url:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=recording.download_url)
        else:
            # Placeholder response - in production would stream from Firebase Storage
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download URL not available"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download recording"
        )

@router.post("/{recording_id}/metadata")
async def update_recording_metadata(
    recording_id: str,
    metadata: RecordingMetadata,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Update recording metadata
    """
    try:
        recording_uuid = UUID(recording_id)
        
        # Check if recording exists
        recording = recording_repo.find_by_id(recording_uuid)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Prepare metadata dictionary
        metadata_dict = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "is_public": metadata.is_public,
            "updated_by": str(current_user.id),
            "updated_at": recording_repo.firebase.get_server_timestamp()
        }
        
        # Update metadata using repository
        success = recording_repo.update_recording_metadata(recording_uuid, metadata_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update recording metadata"
            )
        
        return {"message": "Recording metadata updated successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: str,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a recording
    """
    try:
        recording_uuid = UUID(recording_id)
        
        # Check if recording exists
        recording = recording_repo.find_by_id(recording_uuid)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Check permissions - simplified (in production, verify user is owner/participant)
        
        # Delete recording using repository
        success = recording_repo.delete(recording_uuid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete recording"
            )
        
        return {"message": "Recording deleted successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{recording_id}/share")
async def share_recording(recording_id: str):
    """
    Generate shareable link for recording
    """
    try:
        # TODO: Implement recording sharing
        # 1. Generate temporary access token
        # 2. Create shareable URL
        
        return {
            "share_url": f"https://voiceapp.com/shared/recordings/{recording_id}?token=abc123",
            "expires_at": "2023-12-02T10:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{recording_id}/transcript")
async def get_recording_transcript(recording_id: str):
    """
    Get recording transcript
    """
    try:
        # TODO: Implement transcript retrieval
        return {
            "transcript": [
                {
                    "speaker": "user-1",
                    "timestamp": "00:00:05",
                    "text": "Hello, how are you doing today?"
                },
                {
                    "speaker": "ai-host",
                    "timestamp": "00:00:08",
                    "text": "I'm doing great! Let's talk about technology trends."
                },
                {
                    "speaker": "user-2",
                    "timestamp": "00:00:12",
                    "text": "That sounds interesting. What do you think about AI?"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found"
        ) 