"""
Recording Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from domain.entities import Recording, RecordingStatus, new_recording
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
                    {"field": "participants", "operator": "array-contains", "value": str(user_id)}
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