"""
Recording Repository implementation using Firebase
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from domain.entities import Recording, RecordingStatus, RecordingSegment
# --- RecordingSegmentRepository for subcollections ---

from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

class RecordingSegmentRepository:
    """
    Firestore subcollection repository for recording segments.
    Layout: recordings/{recording_id}/segments/{doc_id}
    Idempotency: doc_id = 'seg-{segment_index}'
    """
    ROOT_COLLECTION = "recordings"
    SUB_COLLECTION = "segments"

    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.db = firebase_service.db

    @staticmethod
    def _seg_doc_id(segment_index: int) -> str:
        return f"seg-{segment_index}"

    def _segments_coll_ref(self, recording_id: UUID):
        return self.db.collection(self.Root_COLLECTION if hasattr(self, 'Root_COLLECTION') else self.ROOT_COLLECTION).document(str(recording_id)).collection(self.SUB_COLLECTION)

    @staticmethod
    def _to_dict(seg: RecordingSegment) -> Dict[str, Any]:
        return {
            "id": str(seg.id),
            "recording_id": str(seg.recording_id),
            "segment_index": seg.segment_index,
            "start_ms": seg.start_ms,
            "end_ms": seg.end_ms,
            "duration_ms": seg.duration_ms,
            "download_url": seg.download_url,
            "created_at": seg.created_at,
            "updated_at": seg.updated_at,
            "meta": seg.meta or {},
        }

    @staticmethod
    def _from_dict(d: Dict[str, Any]) -> RecordingSegment:
        return RecordingSegment(
            id=UUID(d["id"]),
            recording_id=UUID(d["recording_id"]),
            segment_index=int(d["segment_index"]),
            start_ms=int(d["start_ms"]),
            end_ms=int(d["end_ms"]),
            duration_ms=int(d.get("duration_ms", d["end_ms"] - d["start_ms"])),
            download_url=d.get("download_url"),
            created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d.get("created_at"), str) else d.get("created_at"),
            updated_at=datetime.fromisoformat(d["updated_at"]) if isinstance(d.get("updated_at"), str) and d.get("updated_at") else d.get("updated_at"),
            meta=d.get("meta", {}),
        )

    def upsert_many(self, recording_id: UUID, segments: List[RecordingSegment]) -> None:
        if not segments:
            return
        coll_ref = self._segments_coll_ref(recording_id)
        batch_items = []
        for seg in segments:
            doc_id = self._seg_doc_id(seg.segment_index)
            batch_items.append((coll_ref.path, doc_id, self._to_dict(seg)))
        self.firebase.batch_upsert(batch_items)

    def upsert_one(self, recording_id: UUID, segment: RecordingSegment) -> None:
        coll_ref = self._segments_coll_ref(recording_id)
        doc_id = self._seg_doc_id(segment.segment_index)
        coll_ref.document(doc_id).set(self._to_dict(segment), merge=True)

    def get_one(self, recording_id: UUID, segment_index: int) -> Optional[RecordingSegment]:
        coll_ref = self._segments_coll_ref(recording_id)
        doc = coll_ref.document(self._seg_doc_id(segment_index)).get()
        if not doc.exists:
            return None
        return self._from_dict(doc.to_dict())

    def list_by_recording(self, recording_id: UUID, limit: int = 50, offset: int = 0, order: str = "asc") -> List[RecordingSegment]:
        coll_ref = self._segments_coll_ref(recording_id)
        direction = "ASCENDING" if order == "asc" else "DESCENDING"
        from google.cloud.firestore import Query
        q = coll_ref.order_by("segment_index", direction=(Query.ASCENDING if order == "asc" else Query.DESCENDING))
        if limit:
            q = q.limit(limit + offset if offset else limit)
        docs = list(q.stream())
        rows = [d.to_dict() for d in docs]
        if offset:
            rows = rows[offset: offset + limit]
        return [self._from_dict(d) for d in rows]

    def delete_one(self, recording_id: UUID, segment_index: int) -> None:
        coll_ref = self._segments_coll_ref(recording_id)
        coll_ref.document(self._seg_doc_id(segment_index)).delete()

    def delete_all_by_recording(self, recording_id: UUID) -> int:
        coll_ref = self._segments_coll_ref(recording_id)
        total = 0
        while True:
            docs = list(coll_ref.limit(300).stream())
            if not docs:
                break
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()
            total += len(docs)
        return total

    def count_by_recording(self, recording_id: UUID) -> int:
        coll_ref = self._segments_coll_ref(recording_id)
        return sum(1 for _ in coll_ref.stream())
from infrastructure.db.firebase import FirebaseAdminService

logger = logging.getLogger(__name__)


class RecordingRepository:
    """
    Recording repository implementation using Firebase Firestore
    """
    
    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.collection_name = "recordings"
    
    def save(self, recording: Recording) -> Recording:
        """
        Save recording to Firebase Firestore
        
        Args:
            recording: Recording entity to save
            
        Returns:
            Saved recording entity
        """
        try:
            recording_data = self._entity_to_dict(recording)
            
            # Save to Firestore
            self.firebase.add_document(
                self.collection_name,
                recording_data,
                str(recording.id)
            )
            
            logger.info(f"✅ Recording saved successfully: {recording.id}")
            return recording
            
        except Exception as e:
            logger.error(f"❌ Failed to save recording {recording.id}: {e}")
            raise
    
    def find_by_id(self, recording_id: UUID) -> Optional[Recording]:
        """
        Find recording by ID
        
        Args:
            recording_id: Recording's UUID
            
        Returns:
            Recording entity or None if not found
        """
        try:
            recording_data = self.firebase.get_document(
                self.collection_name,
                str(recording_id)
            )
            
            if recording_data:
                return self._dict_to_entity(recording_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find recording {recording_id}: {e}")
            return None
    
    def find_by_user_id(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[Recording]:
        """
        Find recordings by user ID
        
        Args:
            user_id: User's UUID
            limit: Maximum number of recordings to return
            offset: Number of recordings to skip
            
        Returns:
            List of recording entities
        """
        try:
            recordings_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "participants", "operator": "array_contains", "value": str(user_id)}
                ],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(recording_data) for recording_data in recordings_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find recordings for user {user_id}: {e}")
            return []
    
    def find_by_room_id(self, room_id: UUID, limit: int = 20) -> List[Recording]:
        """
        Find recordings by room ID
        
        Args:
            room_id: Room's UUID
            limit: Maximum number of recordings to return
            
        Returns:
            List of recording entities
        """
        try:
            recordings_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "room_id", "operator": "==", "value": str(room_id)}
                ],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(recording_data) for recording_data in recordings_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find recordings for room {room_id}: {e}")
            return []
    
    def find_by_topic(self, topic: str, limit: int = 20) -> List[Recording]:
        """
        Find recordings by topic
        
        Args:
            topic: Topic to filter by
            limit: Maximum number of recordings to return
            
        Returns:
            List of recording entities
        """
        try:
            recordings_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "topic", "operator": "==", "value": topic},
                    {"field": "status", "operator": "==", "value": "ready"}
                ],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(recording_data) for recording_data in recordings_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find recordings by topic {topic}: {e}")
            return []
    
    def find_ready_recordings(self, limit: int = 20, offset: int = 0) -> List[Recording]:
        """
        Find all ready recordings
        
        Args:
            limit: Maximum number of recordings to return
            offset: Number of recordings to skip
            
        Returns:
            List of ready recording entities
        """
        try:
            recordings_data = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "status", "operator": "==", "value": "ready"}],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(recording_data) for recording_data in recordings_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find ready recordings: {e}")
            return []
    
    def update_recording_status(self, recording_id: UUID, status: RecordingStatus) -> bool:
        """
        Update recording status
        
        Args:
            recording_id: Recording's UUID
            status: New status
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                "status": status.name.lower(),
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            self.firebase.update_document(
                self.collection_name,
                str(recording_id),
                update_data
            )
            
            logger.info(f"✅ Recording {recording_id} status updated to {status.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update recording {recording_id}: {e}")
            return False
    
    def update_recording_metadata(self, recording_id: UUID, metadata: dict) -> bool:
        """
        Update recording metadata
        
        Args:
            recording_id: Recording's UUID
            metadata: New metadata
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                "metadata": metadata,
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            self.firebase.update_document(
                self.collection_name,
                str(recording_id),
                update_data
            )
            
            logger.info(f"✅ Recording {recording_id} metadata updated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update recording metadata {recording_id}: {e}")
            return False
    
    def update_download_url(self, recording_id: UUID, download_url: str) -> bool:
        """
        Update recording download URL
        
        Args:
            recording_id: Recording's UUID
            download_url: New download URL
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                "download_url": download_url,
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            self.firebase.update_document(
                self.collection_name,
                str(recording_id),
                update_data
            )
            
            logger.info(f"✅ Recording {recording_id} download URL updated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update recording download URL {recording_id}: {e}")
            return False
    
    def delete(self, recording_id: UUID) -> bool:
        """
        Delete recording
        
        Args:
            recording_id: Recording's UUID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.firebase.delete_document(
                self.collection_name,
                str(recording_id)
            )
            
            logger.info(f"✅ Recording {recording_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete recording {recording_id}: {e}")
            return False
    
    def get_download_url(self, recording_id: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get download URL for recording file
        
        Args:
            recording_id: Recording ID
            expires_in: URL expiration time in seconds
            
        Returns:
            Signed download URL or None if not found
        """
        try:
            # For now, return a mock URL since we don't have actual file storage configured
            # In production, this would generate a signed URL from Firebase Storage or S3
            logger.info(f"🔗 Generating download URL for recording: {recording_id}")
            
            # Check if recording exists
            recording = self.find_by_id(UUID(recording_id))
            if not recording:
                logger.warning(f"⚠️ Recording not found: {recording_id}")
                return None
            
            # Mock download URL for development
            mock_url = f"https://storage.example.com/recordings/{recording_id}.wav"
            logger.info(f"✅ Generated mock download URL: {mock_url}")
            
            return mock_url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate download URL for {recording_id}: {e}")
            return None

    def get_file_metadata(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata for recording
        
        Args:
            recording_id: Recording ID
            
        Returns:
            File metadata or None if not found
        """
        try:
            recording = self.find_by_id(UUID(recording_id))
            if not recording:
                return None
            
            # Mock file metadata
            metadata = {
                "file_size": 1024 * 1024,  # 1MB
                "duration": 120,  # 2 minutes
                "format": "wav",
                "sample_rate": 16000,
                "channels": 1,
                "created_at": recording.created_at.isoformat(),
                "storage_path": f"recordings/{recording_id}.wav"
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to get file metadata for {recording_id}: {e}")
            return None
    
    def _entity_to_dict(self, recording: Recording) -> dict:
        """Convert Recording entity to dictionary"""
        return {
            "id": str(recording.id),
            "room_id": str(recording.room_id),
            "room_name": recording.room_name,
            "topic": recording.topic,
            "participants": [str(p) for p in recording.participants],
            "duration": recording.duration,
            "file_size": recording.file_size,
            "created_at": recording.created_at.isoformat(),
            "updated_at": recording.updated_at.isoformat() if recording.updated_at else None,
            "status": recording.status.name.lower(),
            "download_url": recording.download_url,
            "metadata": recording.metadata or {},
            "transcript": recording.transcript,
            "is_public": recording.is_public,
            "creator_id": str(recording.creator_id) if recording.creator_id else None
        }
    
    def _dict_to_entity(self, data: dict) -> Recording:
        """Convert dictionary to Recording entity"""
        return Recording(
            id=UUID(data["id"]),
            room_id=UUID(data["room_id"]),
            room_name=data["room_name"],
            topic=data["topic"],
            participants=[UUID(p) for p in data.get("participants", [])],
            duration=data.get("duration", 0),
            file_size=data.get("file_size", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            status=RecordingStatus[data["status"].upper()],
            download_url=data.get("download_url"),
            metadata=data.get("metadata", {}),
            transcript=data.get("transcript"),
            is_public=data.get("is_public", False),
            creator_id=UUID(data["creator_id"]) if data.get("creator_id") else None
        ) 