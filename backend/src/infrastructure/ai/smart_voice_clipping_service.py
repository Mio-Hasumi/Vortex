"""
Smart Voice Clipping Service
Handles real-time audio recording and hashtag-based voice clipping
"""

import asyncio
import io
import logging
from collections import deque
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import base64

from domain.entities import SmartVoiceClip, new_smart_voice_clip
from infrastructure.repositories.smart_voice_clip_repository import SmartVoiceClipRepository
from infrastructure.ai.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class HashtagDetection:
    """Result of hashtag detection in audio"""
    def __init__(self, hashtag: str, confidence: float, mention_time_ms: int, transcription: str):
        self.hashtag = hashtag
        self.confidence = confidence
        self.mention_time_ms = mention_time_ms
        self.transcription = transcription


class ChatRoomRecordingSession:
    """Recording session for a chat room"""
    def __init__(self, room_id: UUID, hashtags: List[str], max_buffer_duration_ms: int = 300000):  # 5 minutes
        self.room_id = room_id
        self.hashtags = hashtags
        self.max_buffer_duration_ms = max_buffer_duration_ms
        self.audio_buffer = deque()  # (timestamp_ms, audio_chunk)
        self.start_time = datetime.now(timezone.utc)
        self.is_active = True
        self.clips_created = 0
        self.last_clip_time_ms = 0
        self.min_time_between_clips_ms = 30000  # 30 seconds between clips
    
    def add_audio_chunk(self, audio_chunk: bytes, timestamp_ms: int):
        """Add audio chunk to buffer"""
        if not self.is_active:
            return
        
        self.audio_buffer.append((timestamp_ms, audio_chunk))
        
        # Remove old chunks to keep buffer size manageable
        current_time = int((datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000)
        while (self.audio_buffer and 
               current_time - self.audio_buffer[0][0] > self.max_buffer_duration_ms):
            self.audio_buffer.popleft()
    
    def get_audio_around_time(self, target_time_ms: int, duration_ms: int = 30000) -> Optional[bytes]:
        """Get audio data around a specific time"""
        if not self.audio_buffer:
            return None
        
        # Find chunks within the time range
        start_time = target_time_ms - (duration_ms // 2)  # 15 seconds before
        end_time = target_time_ms + (duration_ms // 2)    # 15 seconds after
        
        relevant_chunks = []
        for timestamp_ms, audio_chunk in self.audio_buffer:
            if start_time <= timestamp_ms <= end_time:
                relevant_chunks.append(audio_chunk)
        
        if not relevant_chunks:
            return None
        
        # Concatenate chunks (simplified - in production, you'd want proper audio concatenation)
        return b''.join(relevant_chunks)
    
    def can_create_clip(self, current_time_ms: int) -> bool:
        """Check if enough time has passed since last clip"""
        return current_time_ms - self.last_clip_time_ms >= self.min_time_between_clips_ms
    
    def mark_clip_created(self, current_time_ms: int):
        """Mark that a clip was created"""
        self.last_clip_time_ms = current_time_ms
        self.clips_created += 1


class SmartVoiceClippingService:
    """Main service for smart voice clipping"""
    
    def __init__(self, 
                 clip_repository: SmartVoiceClipRepository,
                 openai_service: OpenAIService):
        self.clip_repository = clip_repository
        self.openai_service = openai_service
        self.recording_sessions: Dict[UUID, ChatRoomRecordingSession] = {}
        self.processing_queue = asyncio.Queue()
        
        # Start background processing
        asyncio.create_task(self._process_audio_queue())
    
    async def start_room_recording(self, room_id: UUID, hashtags: List[str]) -> bool:
        """Start recording for a chat room"""
        try:
            if room_id in self.recording_sessions:
                logger.warning(f"⚠️ Recording already active for room {room_id}")
                return False
            
            session = ChatRoomRecordingSession(room_id, hashtags)
            self.recording_sessions[room_id] = session
            
            logger.info(f"🎙️ Started recording for room {room_id} with hashtags: {hashtags}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start recording for room {room_id}: {e}")
            return False
    
    async def process_audio_chunk(self, room_id: UUID, audio_chunk: bytes, timestamp_ms: int = None) -> bool:
        """Process incoming audio chunk and check for hashtag mentions"""
        try:
            if room_id not in self.recording_sessions:
                return False
            
            session = self.recording_sessions[room_id]
            if not session.is_active:
                return False
            
            # Use current time if timestamp not provided
            if timestamp_ms is None:
                current_time = datetime.now(timezone.utc)
                timestamp_ms = int((current_time - session.start_time).total_seconds() * 1000)
            
            # Add to buffer
            session.add_audio_chunk(audio_chunk, timestamp_ms)
            
            # Add to processing queue for hashtag detection
            await self.processing_queue.put((room_id, audio_chunk, timestamp_ms))
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to process audio chunk for room {room_id}: {e}")
            return False
    
    async def stop_room_recording(self, room_id: UUID) -> Dict[str, Any]:
        """Stop recording for a room and return summary"""
        try:
            if room_id not in self.recording_sessions:
                return {"error": "No active recording session"}
            
            session = self.recording_sessions[room_id]
            session.is_active = False
            
            # Get final summary
            summary = self.clip_repository.get_room_clips_summary(room_id)
            summary["clips_created"] = session.clips_created
            summary["recording_duration_seconds"] = (datetime.now(timezone.utc) - session.start_time).total_seconds()
            
            # Clean up
            del self.recording_sessions[room_id]
            
            logger.info(f"🛑 Stopped recording for room {room_id}. Created {session.clips_created} clips.")
            return summary
        except Exception as e:
            logger.error(f"❌ Failed to stop recording for room {room_id}: {e}")
            return {"error": str(e)}
    
    async def _process_audio_queue(self):
        """Background task to process audio chunks for hashtag detection"""
        while True:
            try:
                room_id, audio_chunk, timestamp_ms = await self.processing_queue.get()
                
                if room_id not in self.recording_sessions:
                    continue
                
                session = self.recording_sessions[room_id]
                if not session.is_active:
                    continue
                
                # Check if we can create a new clip
                if not session.can_create_clip(timestamp_ms):
                    continue
                
                # Detect hashtags in audio
                detection = await self._detect_hashtag_mention(audio_chunk, session.hashtags)
                
                if detection:
                    await self._create_voice_clip(session, detection, timestamp_ms)
                
                # Mark queue item as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Error processing audio queue: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop
    
    async def _detect_hashtag_mention(self, audio_chunk: bytes, target_hashtags: List[str]) -> Optional[HashtagDetection]:
        """Detect if any target hashtags are mentioned in audio"""
        try:
            # Convert audio to text using OpenAI Whisper
            audio_buffer = io.BytesIO(audio_chunk)
            audio_buffer.name = "audio_chunk.wav"
            
            stt_result = await self.openai_service.speech_to_text(
                audio_file=audio_buffer,
                language="en-US"
            )
            
            transcription = stt_result.get("text", "").lower()
            if not transcription.strip():
                return None
            
            # Check for hashtag mentions
            for hashtag in target_hashtags:
                hashtag_lower = hashtag.lower().replace("#", "")
                
                # Direct hashtag mention
                if f"#{hashtag_lower}" in transcription or hashtag_lower in transcription:
                    confidence = 0.9  # High confidence for direct mention
                    return HashtagDetection(
                        hashtag=hashtag,
                        confidence=confidence,
                        mention_time_ms=0,  # Will be set by caller
                        transcription=transcription
                    )
                
                # Check for related terms (simplified)
                related_terms = self._get_related_terms(hashtag_lower)
                for term in related_terms:
                    if term in transcription:
                        confidence = 0.7  # Medium confidence for related terms
                        return HashtagDetection(
                            hashtag=hashtag,
                            confidence=confidence,
                            mention_time_ms=0,
                            transcription=transcription
                        )
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to detect hashtag mention: {e}")
            return None
    
    def _get_related_terms(self, hashtag: str) -> List[str]:
        """Get related terms for a hashtag (simplified mapping)"""
        related_terms_map = {
            "ai": ["artificial intelligence", "machine learning", "ml", "neural", "algorithm"],
            "technology": ["tech", "software", "hardware", "digital", "computer"],
            "future": ["tomorrow", "next", "coming", "ahead", "forward"],
            "business": ["company", "startup", "entrepreneur", "market", "industry"],
            "science": ["research", "study", "experiment", "discovery", "theory"],
            "health": ["medical", "healthcare", "medicine", "wellness", "fitness"],
            "education": ["learning", "teaching", "school", "university", "student"],
            "environment": ["climate", "green", "sustainable", "eco", "nature"]
        }
        
        return related_terms_map.get(hashtag.lower(), [])
    
    async def _create_voice_clip(self, session: ChatRoomRecordingSession, detection: HashtagDetection, timestamp_ms: int):
        """Create a 30-second voice clip around hashtag mention"""
        try:
            # Get audio data around the mention time
            audio_data = session.get_audio_around_time(timestamp_ms, 30000)  # 30 seconds
            
            if not audio_data:
                logger.warning(f"⚠️ No audio data available for clip at time {timestamp_ms}")
                return
            
            # Create the clip
            clip = new_smart_voice_clip(
                room_id=session.room_id,
                hashtag=detection.hashtag,
                start_time_ms=timestamp_ms - 15000,  # 15 seconds before
                audio_data=audio_data,
                transcription=detection.transcription,
                confidence=detection.confidence,
                meta={
                    "mention_time_ms": timestamp_ms,
                    "detection_method": "direct_mention" if detection.confidence > 0.8 else "related_term",
                    "session_clip_number": session.clips_created + 1
                }
            )
            
            # Save to repository
            self.clip_repository.save(clip)
            
            # Mark clip as created
            session.mark_clip_created(timestamp_ms)
            
            logger.info(f"🎵 Created voice clip for hashtag '{detection.hashtag}' in room {session.room_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create voice clip: {e}")
    
    async def get_room_clips(self, room_id: UUID, hashtag: Optional[str] = None) -> List[SmartVoiceClip]:
        """Get smart voice clips for a room"""
        try:
            if hashtag:
                return self.clip_repository.find_by_room_and_hashtag(room_id, hashtag)
            else:
                return self.clip_repository.find_by_room(room_id)
        except Exception as e:
            logger.error(f"❌ Failed to get clips for room {room_id}: {e}")
            return []
    
    async def get_room_clips_summary(self, room_id: UUID) -> Dict[str, Any]:
        """Get summary of clips for a room"""
        try:
            return self.clip_repository.get_room_clips_summary(room_id)
        except Exception as e:
            logger.error(f"❌ Failed to get clips summary for room {room_id}: {e}")
            return {"error": str(e)}
