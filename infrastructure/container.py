"""
Dependency Injection Container
"""

import logging
from typing import Any, Dict

from infrastructure.db.firebase import FirebaseAdminService

from infrastructure.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
from infrastructure.redis.redis_service import RedisService
from infrastructure.livekit.livekit_service import LiveKitService
from infrastructure.websocket.connection_manager import ConnectionManager
from infrastructure.websocket.event_broadcaster import EventBroadcaster
from infrastructure.config import settings
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.topic_repository import TopicRepository
from infrastructure.repositories.friend_repository import FriendRepository
from infrastructure.repositories.room_repository import RoomRepository
from infrastructure.repositories.recording_repository import RecordingRepository
from infrastructure.repositories.matching_repository import MatchingRepository
# Note: 移除了JWT相关的use cases，现在使用Firebase Auth
from usecase.get_user_profile import GetUserProfileUseCase
from usecase.update_user_profile import UpdateUserProfileUseCase
from usecase.manage_topic_preferences import ManageTopicPreferencesUseCase

logger = logging.getLogger(__name__)


class DIContainer:
    """
    Dependency Injection Container
    Manages all service dependencies and provides them to the application
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """
        Initialize all services and their dependencies
        """
        if self._initialized:
            return
        
        logger.info("🔧 Initializing DI Container...")
        
        # Initialize core services
        self._init_core_services()
        
        # Initialize WebSocket services
        self._init_websocket_services()
        
        # Initialize repositories
        self._init_repositories()
        
        # Initialize use cases
        self._init_use_cases()
        
        # Initialize default data
        self._init_default_data()
        
        self._initialized = True
        logger.info("✅ DI Container initialized successfully")
    
    def _init_core_services(self):
        """Initialize core infrastructure services"""
        
        # Firebase Service (singleton)
        self._services['firebase'] = FirebaseAdminService()
        
        # Redis Service (singleton)
        redis_service = RedisService(settings)
        redis_service.connect()
        self._services['redis'] = redis_service
        
        # LiveKit Service (singleton)
        livekit_service = LiveKitService(settings)
        livekit_service.connect()
        self._services['livekit'] = livekit_service
        

        
        logger.info("✅ Core services initialized")
    
    def _init_websocket_services(self):
        """Initialize WebSocket services"""
        
        redis_service = self._services['redis']
        
        # WebSocket Connection Manager
        connection_manager = ConnectionManager(redis_service)
        self._services['websocket_manager'] = connection_manager
        
        # Event Broadcaster (starts background tasks)
        event_broadcaster = EventBroadcaster(connection_manager, redis_service)
        self._services['event_broadcaster'] = event_broadcaster
        
        logger.info("🔌 WebSocket services initialized")
    
    def _init_repositories(self):
        """Initialize repository services"""
        
        firebase_service = self._services['firebase']
        
        # User Repository
        self._services['user_repo'] = UserRepository(firebase_service)
        
        # Topic Repository
        self._services['topic_repo'] = TopicRepository(firebase_service)
        
        # Friend Repository
        self._services['friend_repo'] = FriendRepository(firebase_service)
        
        # Room Repository
        self._services['room_repo'] = RoomRepository(firebase_service, self._services['livekit'])
        
        # Recording Repository
        self._services['recording_repo'] = RecordingRepository(firebase_service)
        
        # Matching Repository
        self._services['matching_repo'] = MatchingRepository(firebase_service, self._services['redis'])
        
        logger.info("✅ Repositories initialized")
    
    def _init_use_cases(self):
        """Initialize use case services"""
        
        user_repo = self._services['user_repo']
        topic_repo = self._services['topic_repo']
        
        # User profile use cases
        self._services['get_user_profile_usecase'] = GetUserProfileUseCase(user_repo)
        self._services['update_user_profile_usecase'] = UpdateUserProfileUseCase(user_repo)
        
        # Topic preference use case
        self._services['manage_topic_preferences_usecase'] = ManageTopicPreferencesUseCase(user_repo, topic_repo)
        
        # Note: 现在使用Firebase Auth，不需要复杂的JWT use cases
        
        logger.info("✅ Use cases initialized")
    
    def _init_default_data(self):
        """Initialize default data (topics, etc.)"""
        try:
            # Initialize default topics
            topic_repo = self._services['topic_repo']
            topic_repo.ensure_default_topics()
            
            logger.info("✅ Default data initialized")
        except Exception as e:
            # Don't fail the container initialization for default data issues
            logger.warning(f"⚠️ Failed to initialize default data: {e}")
    
    def get_service(self, service_name: str) -> Any:
        """
        Get a service from the container
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            The requested service instance
            
        Raises:
            KeyError: If service is not found
        """
        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found in container")
        
        return self._services[service_name]
    
    # Convenience methods for commonly used services
    def get_firebase_service(self) -> FirebaseAdminService:
        return self.get_service('firebase')
    
    def get_redis_service(self) -> RedisService:
        return self.get_service('redis')
    
    def get_livekit_service(self) -> LiveKitService:
        return self.get_service('livekit')
    
    def get_websocket_manager(self) -> ConnectionManager:
        return self.get_service('websocket_manager')
    
    def get_event_broadcaster(self) -> EventBroadcaster:
        return self.get_service('event_broadcaster')
    
    def get_user_repository(self) -> UserRepository:
        return self.get_service('user_repo')
    
    def get_topic_repository(self) -> TopicRepository:
        return self.get_service('topic_repo')
    
    def get_friend_repository(self) -> FriendRepository:
        return self.get_service('friend_repo')
    
    def get_room_repository(self) -> RoomRepository:
        return self.get_service('room_repo')
    
    def get_recording_repository(self) -> RecordingRepository:
        return self.get_service('recording_repo')
    
    def get_matching_repository(self) -> MatchingRepository:
        return self.get_service('matching_repo')
    
    def get_manage_topic_preferences_usecase(self) -> ManageTopicPreferencesUseCase:
        return self.get_service('manage_topic_preferences_usecase')
    
    async def start_websocket_services(self):
        """Start WebSocket background services"""
        try:
            event_broadcaster = self.get_event_broadcaster()
            await event_broadcaster.start()
            logger.info("🚀 WebSocket services started")
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket services: {e}")
            raise
    
    async def shutdown(self):
        """
        Shutdown the container and cleanup resources
        """
        if not self._initialized:
            return
        
        logger.info("🛑 Shutting down DI Container...")
        
        try:
            # Stop WebSocket services first
            if 'event_broadcaster' in self._services:
                await self._services['event_broadcaster'].stop()
            
            if 'websocket_manager' in self._services:
                await self._services['websocket_manager'].cleanup()
            
            # Disconnect Redis
            if 'redis' in self._services:
                self._services['redis'].disconnect()
            
            # Disconnect LiveKit
            if 'livekit' in self._services:
                self._services['livekit'].disconnect()
            
            # TODO: Add cleanup logic for other services that need it
            
        except Exception as e:
            logger.error(f"❌ Error during container shutdown: {e}")
        
        self._initialized = False
        logger.info("✅ DI Container shut down successfully")


# Global container instance
container = DIContainer() 