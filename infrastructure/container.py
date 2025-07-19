"""
Dependency injection container
"""

import os
import logging
from typing import Dict, Any, Optional

from infrastructure.config import Settings
from infrastructure.auth.firebase_auth import FirebaseAuth
from infrastructure.db.firebase import FirebaseAdminService
from infrastructure.redis.redis_service import RedisService
from infrastructure.livekit.livekit_service import LiveKitService
from infrastructure.websocket.connection_manager import ConnectionManager
from infrastructure.websocket.event_broadcaster import EventBroadcaster

# Repositories
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.friend_repository import FriendRepository
from infrastructure.repositories.topic_repository import TopicRepository
from infrastructure.repositories.matching_repository import MatchingRepository
from infrastructure.repositories.room_repository import RoomRepository
from infrastructure.repositories.recording_repository import RecordingRepository

# AI Services
from infrastructure.ai.openai_service import OpenAIService
from infrastructure.ai.ai_host_service import AIHostService

# Middleware
from infrastructure.middleware.firebase_auth_middleware import FirebaseAuthMiddleware

logger = logging.getLogger(__name__)

class Container:
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._initialized = False
        
    def initialize(self):
        """Initialize all services"""
        if self._initialized:
            return
            
        logger.info("Initializing dependency injection container...")
        
        # Core services
        self._initialize_core_services()
        
        # Data services
        self._initialize_data_services()
        
        # AI services (NEW: GPT-4o Audio support)
        self._initialize_ai_services()
        
        self._initialized = True
        logger.info("✅ Container initialization completed")
        
    def _initialize_core_services(self):
        """Initialize core infrastructure services"""
        # Settings
        settings = Settings()
        
        # Firebase Auth
        self._instances['firebase_auth'] = FirebaseAuth()
        
        # Database
        self._instances['firebase_db'] = FirebaseAdminService()
        
        # Firebase Auth Middleware (handled directly in middleware file to avoid circular dependency)
        
        # Redis
        redis_service = RedisService(settings)
        redis_service.connect()  # Establish Redis connection
        self._instances['redis_service'] = redis_service
        
        # LiveKit
        livekit_service = LiveKitService(settings)
        livekit_service.connect()  # Establish LiveKit connection
        self._instances['livekit_service'] = livekit_service
        
        # WebSocket management
        self._instances['connection_manager'] = ConnectionManager(
            redis_service=self._instances['redis_service']
        )
        self._instances['event_broadcaster'] = EventBroadcaster(
            connection_manager=self._instances['connection_manager'],
            redis_service=self._instances['redis_service']
        )
        
    def _initialize_data_services(self):
        """Initialize data repositories"""
        db = self._instances['firebase_db']
        redis_service = self._instances['redis_service']
        livekit_service = self._instances['livekit_service']
        
        self._instances['user_repository'] = UserRepository(db)
        self._instances['friend_repository'] = FriendRepository(db)
        self._instances['topic_repository'] = TopicRepository(db)
        self._instances['matching_repository'] = MatchingRepository(
            db, redis_service
        )
        self._instances['room_repository'] = RoomRepository(db, livekit_service)
        self._instances['recording_repository'] = RecordingRepository(db)
        
        # Firebase Auth Middleware is handled directly in middleware file
        
    def _initialize_ai_services(self):
        """Initialize AI services with GPT-4o Audio support"""
        try:
            # Get settings instance
            settings = Settings()
            
            # NEW: Initialize OpenAI service with GPT-4o Audio Preview
            openai_api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            openai_base_url = os.getenv("OPENAI_BASE_URL")  # Optional custom endpoint
            
            # Debug info
            logger.info(f"🔍 Debug - OPENAI_API_KEY found: {bool(openai_api_key)}")
            logger.info(f"🔍 Debug - API Key starts with: {openai_api_key[:10] if openai_api_key else 'None'}...")
            
            if not openai_api_key:
                logger.warning("⚠️ OPENAI_API_KEY not found, AI features will be limited")
                # Create a mock service for development
                self._instances['openai_service'] = None
            else:
                logger.info("🎵 Initializing OpenAI service with GPT-4o Audio Preview...")
                try:
                    self._instances['openai_service'] = OpenAIService(
                        api_key=openai_api_key,
                        base_url=openai_base_url
                    )
                    logger.info("✅ OpenAI service created successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to create OpenAI service: {e}")
                    self._instances['openai_service'] = None
                
            # AI Host Service (enhanced for GPT-4o Audio)
            self._instances['ai_host_service'] = AIHostService(
                openai_service=self._instances.get('openai_service'),
                redis_service=self._instances['redis_service']
            )
            
            logger.info("✅ AI services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI services: {e}")
            # Fallback: create placeholder services
            self._instances['openai_service'] = None
            self._instances['ai_host_service'] = None

    # Core service getters
    def get_firebase_auth(self) -> FirebaseAuth:
        return self._instances['firebase_auth']
        
    def get_firebase_db(self) -> FirebaseAdminService:
        return self._instances['firebase_db']
        
    def get_redis_service(self) -> RedisService:
        return self._instances['redis_service']
        
    def get_livekit_service(self) -> LiveKitService:
        return self._instances['livekit_service']
        
    def get_connection_manager(self) -> ConnectionManager:
        return self._instances['connection_manager']
        
    def get_event_broadcaster(self) -> EventBroadcaster:
        return self._instances['event_broadcaster']
    
    def get_websocket_manager(self) -> ConnectionManager:
        """Return a singleton ConnectionManager"""
        return self._instances['connection_manager']
    
    # Repository getters
    def get_user_repository(self) -> UserRepository:
        return self._instances['user_repository']
        
    def get_friend_repository(self) -> FriendRepository:
        return self._instances['friend_repository']
        
    def get_topic_repository(self) -> TopicRepository:
        return self._instances['topic_repository']
        
    def get_matching_repository(self) -> MatchingRepository:
        return self._instances['matching_repository']
        
    def get_room_repository(self) -> RoomRepository:
        return self._instances['room_repository']
        
    def get_recording_repository(self) -> RecordingRepository:
        return self._instances['recording_repository']
    
    # AI service getters (NEW/UPDATED)
    def get_openai_service(self) -> Optional[OpenAIService]:
        """Get GPT-4o Audio enabled OpenAI service"""
        return self._instances.get('openai_service')
        
    def get_ai_host_service(self) -> Optional[AIHostService]:
        """Get AI host service for conversation management"""
        return self._instances.get('ai_host_service')

    # Lifecycle management methods
    async def start_websocket_services(self):
        """Start WebSocket and real-time services"""
        try:
            logger.info("🔌 Starting WebSocket services...")
            
            # Start event broadcaster
            event_broadcaster = self.get_event_broadcaster()
            if hasattr(event_broadcaster, 'start'):
                await event_broadcaster.start()
            
            logger.info("✅ WebSocket services started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket services: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all services gracefully"""
        try:
            logger.info("🛑 Shutting down services...")
            
            # Stop event broadcaster
            event_broadcaster = self.get_event_broadcaster()
            if hasattr(event_broadcaster, 'stop'):
                await event_broadcaster.stop()
            
            # Cleanup connection manager
            connection_manager = self.get_connection_manager()
            if hasattr(connection_manager, 'cleanup'):
                await connection_manager.cleanup()
            
            # Disconnect Redis
            redis_service = self.get_redis_service()
            if hasattr(redis_service, 'disconnect'):
                redis_service.disconnect()
            
            # Disconnect LiveKit
            livekit_service = self.get_livekit_service()
            if hasattr(livekit_service, 'disconnect'):
                livekit_service.disconnect()
            
            logger.info("✅ Services shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Global container instance
container = Container() 