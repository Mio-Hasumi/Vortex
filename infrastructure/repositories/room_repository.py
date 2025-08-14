"""
Room Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from domain.entities import Room, RoomStatus, new_room
from infrastructure.db.firebase import FirebaseAdminService
from infrastructure.livekit.livekit_service import LiveKitService

logger = logging.getLogger(__name__)


class RoomRepository:
    """
    Room repository implementation using Firebase Firestore and LiveKit
    """
    
    def __init__(self, firebase_service: FirebaseAdminService, livekit_service: LiveKitService):
        self.firebase = firebase_service
        self.livekit = livekit_service
        self.collection_name = "rooms"
    
    async def save(self, room: Room) -> Room:
        """
        Save room to Firebase Firestore and create LiveKit room
        
        Args:
            room: Room entity to save
            
        Returns:
            Saved room entity
        """
        try:
            # Create LiveKit room
            room_name = f"room_{room.id}"
            await self.livekit.create_room(room_name, room.max_participants)
            
            room_data = self._entity_to_dict(room)
            
            # Save to Firestore
            self.firebase.add_document(
                self.collection_name,
                room_data,
                str(room.id)
            )
            
            logger.info(f"✅ Room saved successfully: {room.id}")
            return room
            
        except Exception as e:
            logger.error(f"❌ Failed to save room {room.id}: {e}")
            raise
    
    def find_by_id(self, room_id: UUID) -> Optional[Room]:
        """
        Find room by ID
        
        Args:
            room_id: Room's UUID
            
        Returns:
            Room entity or None if not found
        """
        try:
            room_data = self.firebase.get_document(
                self.collection_name,
                str(room_id)
            )
            
            if room_data:
                return self._dict_to_entity(room_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find room {room_id}: {e}")
            return None
    
    def find_active_rooms(self, limit: int = 20, offset: int = 0) -> List[Room]:
        """
        Find all active and waiting rooms
        
        Args:
            limit: Maximum number of rooms to return
            offset: Number of rooms to skip
            
        Returns:
            List of active and waiting room entities
        """
        try:
            rooms_data = self.firebase.query_documents(
                self.collection_name,
                filters=[],  # No filters - get all rooms
                limit=limit,
                order_by="created_at"
            )
            
            # Sort by created_at in descending order manually
            sorted_rooms = sorted([self._dict_to_entity(room_data) for room_data in rooms_data], 
                                key=lambda x: x.created_at, reverse=True)
            
            return sorted_rooms
            
        except Exception as e:
            logger.error(f"❌ Failed to find active rooms: {e}")
            return []
    
    def find_by_topic_id(self, topic_id: UUID, limit: int = 20) -> List[Room]:
        """
        Find rooms by topic ID
        
        Args:
            topic_id: Topic ID to filter by
            limit: Maximum number of rooms to return
            
        Returns:
            List of room entities
        """
        try:
            rooms_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "topic_id", "operator": "==", "value": str(topic_id)},
                    {"field": "status", "operator": "==", "value": "active"}
                ],
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(room_data) for room_data in rooms_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find rooms by topic {topic_id}: {e}")
            return []
    
    def find_by_participant(self, user_id: UUID) -> List[Room]:
        """
        Find rooms where user is a participant
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of room entities
        """
        try:
            rooms_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "participants", "operator": "array_contains", "value": str(user_id)}
                ],
                order_by="created_at",
                order_direction="desc"
            )
            
            return [self._dict_to_entity(room_data) for room_data in rooms_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to find rooms for participant {user_id}: {e}")
            return []
    
    def update_room_status(self, room_id: UUID, status: RoomStatus) -> bool:
        """
        Update room status
        
        Args:
            room_id: Room's UUID
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
                str(room_id),
                update_data
            )
            
            logger.info(f"✅ Room {room_id} status updated to {status.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update room {room_id}: {e}")
            return False
    
    def update_room_ai_enabled(self, room_id: UUID, ai_enabled: bool) -> bool:
        """
        Update room AI enabled state
        
        Args:
            room_id: Room's UUID
            ai_enabled: AI enabled state
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {
                "ai_enabled": ai_enabled,
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            self.firebase.update_document(
                self.collection_name,
                str(room_id),
                update_data
            )
            
            logger.info(f"✅ Room {room_id} AI state updated to {'enabled' if ai_enabled else 'disabled'}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update room {room_id} AI state: {e}")
            return False
    
    def add_participant(self, room_id: UUID, user_id: UUID) -> bool:
        """
        Add participant to room
        
        Args:
            room_id: Room's UUID
            user_id: User's UUID
            
        Returns:
            True if added successfully
        """
        try:
            # Get current room data
            room_data = self.firebase.get_document(
                self.collection_name,
                str(room_id)
            )
            
            if not room_data:
                logger.error(f"❌ Room {room_id} not found")
                return False
            
            participants = room_data.get("participants", [])
            
            # Check if user is already a participant
            if str(user_id) in participants:
                logger.info(f"User {user_id} is already a participant in room {room_id}")
                return True
            
            # Check room capacity
            max_participants = room_data.get("max_participants", 10)
            if len(participants) >= max_participants:
                logger.error(f"❌ Room {room_id} is full")
                return False
            
            # Add participant
            participants.append(str(user_id))
            
            update_data = {
                "participants": participants,
                "updated_at": self.firebase.get_server_timestamp()
            }
            
            self.firebase.update_document(
                self.collection_name,
                str(room_id),
                update_data
            )
            
            logger.info(f"✅ User {user_id} added to room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add participant to room {room_id}: {e}")
            return False
    
    def remove_participant(self, room_id: UUID, user_id: UUID) -> bool:
        """
        Remove participant from room
        
        Args:
            room_id: Room's UUID
            user_id: User's UUID
            
        Returns:
            True if removed successfully
        """
        try:
            # Get current room data
            room_data = self.firebase.get_document(
                self.collection_name,
                str(room_id)
            )
            
            if not room_data:
                logger.error(f"❌ Room {room_id} not found")
                return False
            
            participants = room_data.get("participants", [])
            
            # Remove participant
            if str(user_id) in participants:
                participants.remove(str(user_id))
                
                update_data = {
                    "participants": participants,
                    "updated_at": self.firebase.get_server_timestamp()
                }
                
                self.firebase.update_document(
                    self.collection_name,
                    str(room_id),
                    update_data
                )
                
                logger.info(f"✅ User {user_id} removed from room {room_id}")
                return True
            else:
                logger.info(f"User {user_id} is not a participant in room {room_id}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove participant from room {room_id}: {e}")
            return False
    
    def delete(self, room_id: UUID) -> bool:
        """
        Delete room
        
        Args:
            room_id: Room's UUID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.firebase.delete_document(
                self.collection_name,
                str(room_id)
            )
            
            logger.info(f"✅ Room {room_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete room {room_id}: {e}")
            return False
    
    def generate_livekit_token(self, room_id: UUID, user_id: UUID) -> str:
        """
        Generate LiveKit token for room access
        
        Args:
            room_id: Room's UUID
            user_id: User's UUID
            
        Returns:
            LiveKit access token
        """
        try:
            return self.livekit.generate_room_token(room_id, user_id)
        except Exception as e:
            logger.error(f"❌ Failed to generate LiveKit token for room {room_id}: {e}")
            # Return a mock token for development
            return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.mock_token"
    
    async def get_room_participants(self, room_id: str) -> List[str]:
        """
        Return the current participant user_id list of the specified room
        Reuse existing find_by_id (synchronous)
        Room.current_participants is assumed to be List[UUID]
        """
        room = self.find_by_id(UUID(room_id))
        if not room:
            return []
        return [str(uid) for uid in room.current_participants]
    
    def find_by_livekit_room_name(self, livekit_name: str) -> Optional[Room]:
        """
        Find room entity by livekit_room_name field
        """
        rooms_data = self.firebase.query_documents(
            self.collection_name,
            filters=[{"field": "livekit_room_name", "operator": "==", "value": livekit_name}]
        )
        if rooms_data:
            return self._dict_to_entity(rooms_data[0])
        return None
    
    def _entity_to_dict(self, room: Room) -> dict:
        """Convert Room entity to dictionary"""
        return {
            "id": str(room.id),
            "name": room.name,
            "topic_id": str(room.topic_id),
            "participants": [str(p) for p in room.current_participants],
            "max_participants": room.max_participants,
            "status": room.status.name.lower(),
            "created_at": room.created_at.isoformat(),
            "started_at": room.started_at.isoformat() if room.started_at else None,
            "ended_at": room.ended_at.isoformat() if room.ended_at else None,
            "livekit_room_name": room.livekit_room_name,
            "host_ai_identity": room.host_ai_identity,
            "is_private": room.is_private,
            "created_by": str(room.created_by),
            "is_recording_enabled": room.is_recording_enabled,
            "recording_id": str(room.recording_id) if room.recording_id else None,
            "ai_enabled": room.ai_enabled
        }
    
    def _dict_to_entity(self, data: dict) -> Room:
        """Convert dictionary to Room entity"""
        return Room(
            id=UUID(data["id"]),
            name=data["name"],
            topic_id=UUID(data["topic_id"]),
            current_participants=[UUID(p) for p in data.get("participants", [])],
            max_participants=data.get("max_participants", 10),
            status=RoomStatus[data["status"].upper()],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            livekit_room_name=data.get("livekit_room_name"),
            host_ai_identity=data.get("host_ai_identity"),
            is_private=data.get("is_private", False),
            created_by=UUID(data["created_by"]),
            is_recording_enabled=data.get("is_recording_enabled", True),
            recording_id=UUID(data["recording_id"]) if data.get("recording_id") else None,
            ai_enabled=data.get("ai_enabled", False)
        ) 