"""
LiveKit Service for room management and token generation
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

try:
    from livekit.api import LiveKitAPI, AccessToken, VideoGrants, Room
    from livekit.api import CreateRoomRequest, DeleteRoomRequest, ListRoomsRequest
    LIVEKIT_AVAILABLE = True
except ImportError:
    # Fallback for development
    LiveKitAPI = None
    AccessToken = None
    VideoGrants = None
    Room = None
    CreateRoomRequest = None
    DeleteRoomRequest = None
    ListRoomsRequest = None
    LIVEKIT_AVAILABLE = False

from infrastructure.config import Settings

logger = logging.getLogger(__name__)


class LiveKitService:
    """LiveKit service for room management and token generation"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[LiveKitAPI] = None
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET
        self.server_url = settings.LIVEKIT_SERVER_URL
        
    def connect(self) -> None:
        """Initialize LiveKit connection"""
        try:
            if not LIVEKIT_AVAILABLE or not self.api_key or not self.api_secret:
                logger.warning("⚠️ LiveKit not available or credentials not configured, using mock client")
                self.client = MockLiveKitClient()
                return
            
            self.client = LiveKitAPI(
                self.server_url,
                self.api_key,
                self.api_secret
            )
            
            logger.info("✅ LiveKit client initialized with real credentials")
            # Note: Connection test will be done on first async operation
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize LiveKit client: {e}")
            self.client = MockLiveKitClient()
            logger.warning("⚠️ Using mock LiveKit client")
    
    def disconnect(self) -> None:
        """Close LiveKit connection"""
        if self.client:
            # LiveKit client doesn't need explicit disconnection
            pass
        logger.info("LiveKit connection closed")
    
    @property
    def is_mock(self) -> bool:
        """Check if using mock client"""
        return isinstance(self.client, MockLiveKitClient)
    
    def health_check(self) -> bool:
        """Check LiveKit health"""
        try:
            if isinstance(self.client, MockLiveKitClient):
                return True
            rooms = self.client.room.list_rooms(ListRoomsRequest())
            return True
        except Exception:
            return False
    
    # Room Management
    async def create_room(self, room_name: str, max_participants: int = 10) -> Dict[str, Any]:
        """
        Create a new room
        
        Args:
            room_name: Name of the room
            max_participants: Maximum number of participants
            
        Returns:
            Room information
        """
        try:
            if isinstance(self.client, MockLiveKitClient):
                # Use mock client
                from types import SimpleNamespace
                request = SimpleNamespace(
                    name=room_name,
                    max_participants=max_participants
                )
                room = self.client.create_room(request)
                return {
                    "name": room.name,
                    "sid": room.sid,
                    "creation_time": room.creation_time,
                    "max_participants": room.max_participants,
                    "num_participants": room.num_participants,
                    "metadata": room.metadata
                }
            
            # Use real LiveKit client
            request = CreateRoomRequest(
                name=room_name,
                max_participants=max_participants,
                empty_timeout=300,  # 5 minutes
                departure_timeout=20  # 20 seconds
            )
            
            room = await self.client.room.create_room(request)
            
            logger.info(f"✅ LiveKit room created: {room_name}")
            return {
                "name": room.name,
                "sid": room.sid,
                "creation_time": room.creation_time,
                "max_participants": room.max_participants,
                "num_participants": room.num_participants,
                "metadata": room.metadata
            }
            
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"🔄 Room {room_name} already exists, retrieving info")
                return await self.get_room_info(room_name)
            else:
                logger.error(f"❌ Failed to create room {room_name}: {e}")
                raise
    
    def delete_room(self, room_name: str) -> bool:
        """
        Delete a room
        
        Args:
            room_name: Name of the room to delete
            
        Returns:
            True if successful
        """
        try:
            if not DeleteRoomRequest:
                logger.warning("⚠️ LiveKit not available, using mock response")
                return True
            
            request = DeleteRoomRequest(room=room_name)
            self.client.room.delete_room(request)
            
            logger.info(f"✅ LiveKit room deleted: {room_name}")
            return True
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(f"⚠️ Room {room_name} not found, already deleted")
                return True
            else:
                logger.error(f"❌ Failed to delete room {room_name}: {e}")
                return False
    
    async def get_room_info(self, room_name: str) -> Optional[Dict[str, Any]]:
        """
        Get room information
        
        Args:
            room_name: Name of the room
            
        Returns:
            Room information or None if not found
        """
        try:
            if isinstance(self.client, MockLiveKitClient):
                # Use mock client
                from types import SimpleNamespace
                request = SimpleNamespace()
                rooms = self.client.list_rooms(request)
                
                for room in rooms.rooms:
                    if room.name == room_name:
                        return {
                            "name": room.name,
                            "sid": room.sid,
                            "creation_time": room.creation_time,
                            "max_participants": room.max_participants,
                            "num_participants": room.num_participants,
                            "metadata": room.metadata
                        }
                return None
            
            # Use real LiveKit client
            rooms = await self.client.room.list_rooms(ListRoomsRequest())
            
            if rooms and hasattr(rooms, 'rooms') and rooms.rooms:
                for room in rooms.rooms:
                    if room.name == room_name:
                        return {
                            "name": room.name,
                            "sid": room.sid,
                            "creation_time": room.creation_time,
                            "max_participants": room.max_participants,
                            "num_participants": room.num_participants,
                            "metadata": room.metadata
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get room info {room_name}: {e}")
            return None
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """
        List all rooms
        
        Returns:
            List of room information
        """
        try:
            if not ListRoomsRequest:
                logger.warning("⚠️ LiveKit not available, using mock response")
                return []
            
            rooms = self.client.room.list_rooms(ListRoomsRequest())
            
            return [
                {
                    "name": room.name,
                    "sid": room.sid,
                    "creation_time": room.creation_time,
                    "max_participants": room.max_participants,
                    "num_participants": room.num_participants,
                    "metadata": room.metadata
                }
                for room in rooms.rooms
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to list rooms: {e}")
            return []
    
    # Token Generation
    def generate_token(
        self,
        room_name: str,
        identity: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
        can_publish_data: bool = True,
        ttl: int = 3600  # 1 hour
    ) -> str:
        """
        Generate access token for a participant
        
        Args:
            room_name: Name of the room
            identity: Participant identity
            can_publish: Can publish audio/video
            can_subscribe: Can subscribe to audio/video
            can_publish_data: Can publish data
            ttl: Token time-to-live in seconds
            
        Returns:
            JWT token
        """
        try:
            if not LIVEKIT_AVAILABLE or not AccessToken or not VideoGrants or not self.api_key or not self.api_secret:
                logger.warning("⚠️ LiveKit not available, using mock token")
                return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.mock_token"
            
            token = AccessToken(self.api_key, self.api_secret)
            
            # Set identity and TTL
            from datetime import timedelta
            token = token.with_identity(identity)
            token = token.with_ttl(timedelta(seconds=ttl))
            
            # Create video grants
            grants = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
                can_publish_data=can_publish_data
            )
            
            token = token.with_grants(grants)
            
            jwt_token = token.to_jwt()
            
            logger.info(f"✅ Generated LiveKit token for {identity} in room {room_name}")
            return jwt_token
            
        except Exception as e:
            logger.error(f"❌ Failed to generate token for {identity}: {e}")
            raise
    
    def generate_room_token(self, room_id: UUID, user_id: UUID) -> str:
        """
        Generate token for a specific room and user
        
        Args:
            room_id: Room UUID
            user_id: User UUID
            
        Returns:
            JWT token
        """
        room_name = f"room_{room_id}"
        identity = f"user_{user_id}"
        
        return self.generate_token(
            room_name=room_name,
            identity=identity,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )
    
    # Participant Management
    def get_participants(self, room_name: str) -> List[Dict[str, Any]]:
        """
        Get participants in a room
        
        Args:
            room_name: Name of the room
            
        Returns:
            List of participant information
        """
        try:
            participants = self.client.room.list_participants(room=room_name)
            
            return [
                {
                    "identity": p.identity,
                    "name": p.name,
                    "sid": p.sid,
                    "state": p.state,
                    "joined_at": p.joined_at,
                    "metadata": p.metadata
                }
                for p in participants.participants
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to get participants for room {room_name}: {e}")
            return []
    
    def remove_participant(self, room_name: str, identity: str) -> bool:
        """
        Remove a participant from a room
        
        Args:
            room_name: Name of the room
            identity: Participant identity
            
        Returns:
            True if successful
        """
        try:
            self.client.room.remove_participant(room=room_name, identity=identity)
            
            logger.info(f"✅ Removed participant {identity} from room {room_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove participant {identity}: {e}")
            return False


class MockLiveKitClient:
    """Mock LiveKit client for development"""
    
    def __init__(self):
        self.rooms = {}
        self.room = self  # Point to self to mimic client.room.method_name() structure
        logger.info("🔧 Mock LiveKit client initialized")
    
    def create_room(self, request) -> Any:
        """Mock create room"""
        room_name = request.name
        if room_name in self.rooms:
            raise Exception(f"Room {room_name} already exists")
        
        class MockRoom:
            def __init__(self, name, sid, creation_time, max_participants, num_participants, metadata):
                self.name = name
                self.sid = sid
                self.creation_time = creation_time
                self.max_participants = max_participants
                self.num_participants = num_participants
                self.metadata = metadata
        
        room = MockRoom(
            name=room_name,
            sid=f"RM_mock_{room_name}",
            creation_time=int(datetime.now().timestamp()),
            max_participants=request.max_participants,
            num_participants=0,
            metadata=""
        )
        self.rooms[room_name] = room
        return room
    
    def delete_room(self, request) -> None:
        """Mock delete room"""
        room_name = request.room
        if room_name not in self.rooms:
            raise Exception(f"Room {room_name} not found")
        del self.rooms[room_name]
    
    def list_rooms(self, request) -> Any:
        """Mock list rooms"""
        class MockRoomsResponse:
            def __init__(self, rooms):
                self.rooms = list(rooms.values())
        
        return MockRoomsResponse(self.rooms)
    
    def list_participants(self, room: str) -> Any:
        """Mock list participants"""
        class MockParticipantsResponse:
            def __init__(self):
                self.participants = []
        
        return MockParticipantsResponse()
    
    def remove_participant(self, room: str, identity: str) -> None:
        """Mock remove participant"""
        pass 