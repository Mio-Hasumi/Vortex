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
async def get_recording_transcript(
    recording_id: str,
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Get recording transcript using OpenAI Whisper
    """
    try:
        import io
        from infrastructure.container import container
        
        # Get recording details
        recording = recording_repo.find_by_id(recording_id)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Check if user has access to this recording
        if recording.created_by != current_user.id:
            # TODO: Add proper permission check (e.g., if user was a participant)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if transcript already exists (cache)
        if hasattr(recording, 'transcript_data') and recording.transcript_data:
            return {"transcript": recording.transcript_data}
        
        # Get audio file URL and download for processing
        download_url = recording_repo.get_download_url(recording_id)
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording file not found"
            )
        
        # Download audio file for STT processing
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to download recording file"
                    )
                
                audio_content = await response.read()
        
        # Create audio buffer for OpenAI
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = f"recording_{recording_id}.wav"
        
        # Get OpenAI service and perform STT
        openai_service = container.get_openai_service()
        stt_result = await openai_service.speech_to_text(
            audio_file=audio_buffer,
            language="en-US"  # Could be configurable
        )
        
        # Parse words for speaker diarization (simplified)
        transcript_entries = []
        words = stt_result.get("words", [])
        
        if words:
            # Group words into segments (simplified speaker detection)
            current_segment = []
            current_speaker = "user-1"
            
            for word in words:
                current_segment.append(word["word"])
                
                # Simple heuristic: new speaker every 30 seconds or sentence break
                if (word.get("end", 0) - (current_segment[0] if current_segment else {"start": 0})["start"] > 30.0 
                    or word["word"].endswith(('.', '!', '?'))):
                    
                    if current_segment:
                        text = " ".join([w["word"] if isinstance(w, dict) else w for w in current_segment])
                        start_time = current_segment[0]["start"] if isinstance(current_segment[0], dict) else 0
                        
                        transcript_entries.append({
                            "speaker": current_speaker,
                            "timestamp": f"{int(start_time//60):02d}:{int(start_time%60):02d}",
                            "text": text.strip(),
                            "start_time": start_time,
                            "confidence": word.get("confidence", 0.0)
                        })
                        
                        # Alternate speaker (simplified)
                        current_speaker = "user-2" if current_speaker == "user-1" else "user-1"
                        current_segment = []
        else:
            # Fallback: single transcript entry
            transcript_entries = [{
                "speaker": "user-1",
                "timestamp": "00:00:00",
                "text": stt_result["text"],
                "start_time": 0,
                "confidence": stt_result.get("confidence", 0.0)
            }]
        
        # Cache the transcript for future requests
        try:
            recording_repo.update_transcript(recording_id, transcript_entries)
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache transcript: {e}")
        
        return {
            "transcript": transcript_entries,
            "language": stt_result.get("language", "unknown"),
            "duration": stt_result.get("duration", 0),
            "processing_info": {
                "model": "whisper-1",
                "processed_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transcript generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transcript: {str(e)}"
        ) 

# NEW: Conversation Summary Endpoint
@router.get("/{recording_id}/summary")
async def get_conversation_summary(
    recording_id: str,
    summary_type: str = "detailed",  # brief, detailed, highlights
    recording_repo = Depends(get_recording_repository),
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-powered conversation summary
    """
    try:
        from infrastructure.container import container
        
        # Get recording details
        recording = recording_repo.find_by_id(recording_id)
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Check permissions
        if recording.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get transcript first
        transcript_response = await get_recording_transcript(
            recording_id, recording_repo, current_user
        )
        transcript_entries = transcript_response["transcript"]
        
        if not transcript_entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript available for summarization"
            )
        
        # Prepare conversation text for summarization
        conversation_text = ""
        speakers = set()
        
        for entry in transcript_entries:
            speaker = entry["speaker"]
            text = entry["text"]
            speakers.add(speaker)
            conversation_text += f"{speaker}: {text}\n"
        
        # Get OpenAI service for summarization
        openai_service = container.get_openai_service()
        
        # Create context for summarization
        context = {
            "conversation_length": len(transcript_entries),
            "duration": transcript_response.get("duration", 0),
            "speakers": list(speakers),
            "summary_type": summary_type
        }
        
        # Generate summary using AI
        summary_response = await openai_service.generate_conversation_summary(
            conversation_text=conversation_text,
            context=context,
            summary_type=summary_type
        )
        
        # Extract key insights and topics
        topics_result = await openai_service.extract_topics_and_hashtags(
            text=conversation_text,
            context={
                "source": "conversation_summary",
                "participants": list(speakers)
            }
        )
        
        return {
            "summary": {
                "brief": summary_response.get("brief_summary", ""),
                "detailed": summary_response.get("detailed_summary", ""),
                "key_points": summary_response.get("key_points", []),
                "highlights": summary_response.get("highlights", []),
                "action_items": summary_response.get("action_items", []),
                "insights": summary_response.get("insights", [])
            },
            "analysis": {
                "main_topics": topics_result.get("main_topics", []),
                "hashtags": topics_result.get("hashtags", []),
                "sentiment": topics_result.get("sentiment", "neutral"),
                "conversation_style": topics_result.get("conversation_style", "casual")
            },
            "metadata": {
                "duration": transcript_response.get("duration", 0),
                "word_count": len(conversation_text.split()),
                "speakers": list(speakers),
                "language": transcript_response.get("language", "unknown"),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Conversation summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        ) 