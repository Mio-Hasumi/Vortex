"""
Dependency Injection Container
"""

import logging
from typing import Any, Dict

from infrastructure.db.firebase import FirebaseAdminService

from infrastructure.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
from infrastructure.redis.redis_service import RedisService
from infrastructure.livekit.livekit_service import LiveKitService
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
        
        # Firebase Auth Middleware (depends on user repository)
        self._services['firebase_auth'] = FirebaseAuthMiddleware(self._services['user_repo'])
        
        logger.info("✅ Repositories initialized")
    
    def _init_use_cases(self):
        """Initialize use case interactors"""
        
        user_repo = self._services['user_repo']
        firebase_service = self._services['firebase']
        
        # Note: 现在使用Firebase Auth，不需要复杂的JWT use cases
        # 认证逻辑移动到Firebase Auth Middleware中
        
        # Profile management use cases
        self._services['get_user_profile'] = GetUserProfileUseCase(user_repo)
        self._services['update_user_profile'] = UpdateUserProfileUseCase(user_repo)
        
        # Topic preference management
        topic_repo = self._services['topic_repo']
        self._services['manage_topic_preferences'] = ManageTopicPreferencesUseCase(
            user_repository=user_repo,
            topic_repository=topic_repo
        )
        
        # Profile and preferences use cases
        self.get_user_profile_use_case = GetUserProfileUseCase(
            self._services['user_repo']
        )
        
        self.update_user_profile_use_case = UpdateUserProfileUseCase(
            self._services['user_repo']
        )
        
        self.manage_topic_preferences_use_case = ManageTopicPreferencesUseCase(
            self._services['user_repo'],
            self._services['topic_repo']
        )
        
        logger.info("✅ Use cases initialized")
    
    def _init_default_data(self):
        """Initialize default data (topics, etc.)"""
        try:
            topic_repo = self._services['topic_repo']
            topic_repo.create_default_topics()
            logger.info("✅ Default data initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize default data: {e}")
    
    def get(self, service_name: str) -> Any:
        """
        Get a service from the container
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not found
        """
        if not self._initialized:
            self.initialize()
        
        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found in container")
        
        return self._services[service_name]
    
    def get_firebase_service(self) -> FirebaseAdminService:
        """Get Firebase service"""
        return self.get('firebase')
    

    
    def get_redis_service(self) -> RedisService:
        """Get Redis service"""
        return self.get('redis')
    
    def get_livekit_service(self) -> LiveKitService:
        """Get LiveKit service"""
        return self.get('livekit')
    
    def get_user_repository(self) -> UserRepository:
        """Get user repository"""
        return self.get('user_repo')
    
    def get_topic_repository(self) -> TopicRepository:
        """Get topic repository"""
        return self.get('topic_repo')
    
    def get_friend_repository(self) -> FriendRepository:
        """Get friend repository"""
        return self.get('friend_repo')
    
    def get_room_repository(self) -> RoomRepository:
        """Get room repository"""
        return self.get('room_repo')
    
    def get_recording_repository(self) -> RecordingRepository:
        """Get recording repository"""
        return self.get('recording_repo')
    
    def get_matching_repository(self) -> MatchingRepository:
        """Get matching repository"""
        return self.get('matching_repo')
    
    def get_firebase_auth_middleware(self) -> FirebaseAuthMiddleware:
        """Get Firebase authentication middleware"""
        return self.get('firebase_auth')
    
    def shutdown(self):
        """
        Shutdown the container and cleanup resources
        """
        if not self._initialized:
            return
        
        logger.info("🛑 Shutting down DI Container...")
        
        # Cleanup Redis connections
        if 'redis' in self._services:
            self._services['redis'].disconnect()
        
        # Cleanup LiveKit connections
        if 'livekit' in self._services:
            self._services['livekit'].disconnect()
        
        # TODO: Add cleanup logic for other services that need it
        # e.g., close database connections, cleanup caches, etc.
        
        self._services.clear()
        self._initialized = False
        
        logger.info("✅ DI Container shut down successfully")


# Global container instance
container = DIContainer() 