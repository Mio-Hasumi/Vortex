"""
Smart Voice Clip Repository
Handles storage and retrieval of smart voice clips
"""

import logging
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

from infrastructure.db.firebase import FirebaseAdminService
from domain.entities import SmartVoiceClip

logger = logging.getLogger(__name__)


class SmartVoiceClipRepository:
    """
    Repository for smart voice clips using Firebase Firestore
    """
    
    COLLECTION_NAME = "smart_voice_clips"
    
    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.db = firebase_service.db
        self.collection = self.db.collection(self.COLLECTION_NAME)
    
    def save(self, clip: SmartVoiceClip) -> SmartVoiceClip:
        """Save a smart voice clip"""
        try:
            doc_data = self._to_dict(clip)
            self.collection.document(str(clip.id)).set(doc_data)
            logger.info(f"💾 Saved smart voice clip {clip.id} for room {clip.room_id}")
            return clip
        except Exception as e:
            logger.error(f"❌ Failed to save smart voice clip: {e}")
            raise
    
    def find_by_id(self, clip_id: UUID) -> Optional[SmartVoiceClip]:
        """Find a smart voice clip by ID"""
        try:
            doc = self.collection.document(str(clip_id)).get()
            if doc.exists:
                return self._from_dict(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"❌ Failed to find smart voice clip {clip_id}: {e}")
            return None
    
    def find_by_room(self, room_id: UUID, limit: int = 50, offset: int = 0) -> List[SmartVoiceClip]:
        """Find all smart voice clips for a room"""
        try:
            query = self.collection.where("room_id", "==", str(room_id)).order_by("start_time_ms")
            if limit:
                query = query.limit(limit + offset if offset else limit)
            
            docs = list(query.stream())
            clips = [self._from_dict(doc.to_dict()) for doc in docs]
            
            if offset:
                clips = clips[offset:offset + limit]
            
            logger.info(f"🔍 Found {len(clips)} smart voice clips for room {room_id}")
            return clips
        except Exception as e:
            logger.error(f"❌ Failed to find clips for room {room_id}: {e}")
            return []
    
    def find_by_room_and_hashtag(self, room_id: UUID, hashtag: str, limit: int = 50) -> List[SmartVoiceClip]:
        """Find smart voice clips for a room filtered by hashtag"""
        try:
            query = (self.collection
                    .where("room_id", "==", str(room_id))
                    .where("hashtag", "==", hashtag)
                    .order_by("start_time_ms")
                    .limit(limit))
            
            docs = list(query.stream())
            clips = [self._from_dict(doc.to_dict()) for doc in docs]
            
            logger.info(f"🔍 Found {len(clips)} clips for room {room_id} with hashtag {hashtag}")
            return clips
        except Exception as e:
            logger.error(f"❌ Failed to find clips for room {room_id} hashtag {hashtag}: {e}")
            return []
    
    def delete_by_room(self, room_id: UUID) -> int:
        """Delete all smart voice clips for a room"""
        try:
            query = self.collection.where("room_id", "==", str(room_id))
            docs = list(query.stream())
            
            if not docs:
                return 0
            
            # Delete in batches
            batch = self.db.batch()
            deleted_count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Commit batch every 500 operations
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining operations
            if deleted_count % 500 != 0:
                batch.commit()
            
            logger.info(f"🗑️ Deleted {deleted_count} smart voice clips for room {room_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Failed to delete clips for room {room_id}: {e}")
            return 0
    
    def get_room_clips_summary(self, room_id: UUID) -> Dict[str, Any]:
        """Get summary statistics for room clips"""
        try:
            clips = self.find_by_room(room_id, limit=1000)  # Get all clips
            
            if not clips:
                return {
                    "total_clips": 0,
                    "hashtags": [],
                    "total_duration_seconds": 0,
                    "clips_by_hashtag": {}
                }
            
            # Group by hashtag
            clips_by_hashtag = {}
            total_duration = 0
            hashtags = set()
            
            for clip in clips:
                hashtag = clip.hashtag
                hashtags.add(hashtag)
                total_duration += clip.duration_ms
                
                if hashtag not in clips_by_hashtag:
                    clips_by_hashtag[hashtag] = []
                clips_by_hashtag[hashtag].append({
                    "id": str(clip.id),
                    "start_time_ms": clip.start_time_ms,
                    "transcription": clip.transcription[:100] + "..." if len(clip.transcription) > 100 else clip.transcription,
                    "confidence": clip.confidence
                })
            
            return {
                "total_clips": len(clips),
                "hashtags": list(hashtags),
                "total_duration_seconds": total_duration / 1000.0,
                "clips_by_hashtag": clips_by_hashtag
            }
        except Exception as e:
            logger.error(f"❌ Failed to get clips summary for room {room_id}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _to_dict(clip: SmartVoiceClip) -> Dict[str, Any]:
        """Convert SmartVoiceClip to dictionary for Firestore"""
        return {
            "id": str(clip.id),
            "room_id": str(clip.room_id),
            "hashtag": clip.hashtag,
            "start_time_ms": clip.start_time_ms,
            "end_time_ms": clip.end_time_ms,
            "duration_ms": clip.duration_ms,
            "audio_data": clip.audio_data,  # Store as bytes
            "transcription": clip.transcription,
            "confidence": clip.confidence,
            "created_at": clip.created_at,
            "download_url": clip.download_url,
            "meta": clip.meta or {}
        }
    
    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> SmartVoiceClip:
        """Convert Firestore document to SmartVoiceClip"""
        return SmartVoiceClip(
            id=UUID(data["id"]),
            room_id=UUID(data["room_id"]),
            hashtag=data["hashtag"],
            start_time_ms=data["start_time_ms"],
            end_time_ms=data["end_time_ms"],
            duration_ms=data["duration_ms"],
            audio_data=data["audio_data"],  # Load as bytes
            transcription=data["transcription"],
            confidence=data["confidence"],
            created_at=data["created_at"],
            download_url=data.get("download_url"),
            meta=data.get("meta", {})
        )
