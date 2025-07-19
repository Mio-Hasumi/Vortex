"""
AI Host Service for VoiceApp

Manages AI-driven conversation flow:
1. User greeting and topic inquiry  
2. Dynamic topic extraction and hashtag generation
3. Intelligent user matching based on hashtags
4. Conversation hosting and guidance
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import json

from .openai_service import OpenAIService

logger = logging.getLogger(__name__)


class AIHostSession:
    """
    Represents an AI host session with a user
    """
    
    def __init__(self, user_id: UUID, session_id: str = None):
        self.session_id = session_id or str(uuid4())
        self.user_id = user_id
        self.state = "greeting"  # greeting -> topic_inquiry -> matching -> hosting
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Session data
        self.conversation_history = []
        self.extracted_topics = []
        self.generated_hashtags = []
        self.user_context = {}
        self.current_room_id = None
        self.matched_users = []
        
        # AI preferences
        self.tts_voice = "nova"
        self.language = "en-US"
        self.conversation_style = "casual"

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "conversation_history": self.conversation_history,
            "extracted_topics": self.extracted_topics,
            "generated_hashtags": self.generated_hashtags,
            "user_context": self.user_context,
            "current_room_id": self.current_room_id,
            "matched_users": [str(u) for u in self.matched_users] if self.matched_users else [],
            "tts_voice": self.tts_voice,
            "language": self.language,
            "conversation_style": self.conversation_style
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIHostSession':
        """Create session from dictionary"""
        session = cls(UUID(data["user_id"]), data["session_id"])
        session.state = data.get("state", "greeting")
        session.created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        session.last_activity = datetime.fromisoformat(data["last_activity"].replace('Z', '+00:00'))
        session.conversation_history = data.get("conversation_history", [])
        session.extracted_topics = data.get("extracted_topics", [])
        session.generated_hashtags = data.get("generated_hashtags", [])
        session.user_context = data.get("user_context", {})
        session.current_room_id = data.get("current_room_id")
        session.matched_users = [UUID(u) for u in data.get("matched_users", [])]
        session.tts_voice = data.get("tts_voice", "nova")
        session.language = data.get("language", "en-US")
        session.conversation_style = data.get("conversation_style", "casual")
        return session


class AIHostService:
    """
    AI Host Service for managing conversation flow
    """
    
    def __init__(self, openai_service: OpenAIService, redis_service=None):
        self.openai = openai_service
        self.redis = redis_service
        self.active_sessions: Dict[str, AIHostSession] = {}  # In-memory cache
        
        # Session timeouts
        self.session_timeout = timedelta(hours=2)  # 2 hours max session
        self.idle_timeout = timedelta(minutes=30)   # 30 min idle timeout
        
        logger.info("✅ AI Host Service initialized")

    async def start_session(self, user_id: UUID, user_context: Dict[str, Any] = None) -> AIHostSession:
        """
        Start a new AI host session for a user
        
        Args:
            user_id: User's UUID
            user_context: User profile and preferences
            
        Returns:
            New AI host session
        """
        try:
            logger.info(f"🎭 Starting AI host session for user: {user_id}")
            
            # Check if user already has an active session
            existing_session = await self.get_active_session(user_id)
            if existing_session:
                logger.info(f"♻️ Found existing session: {existing_session.session_id}")
                return existing_session
            
            # Create new session
            session = AIHostSession(user_id)
            session.user_context = user_context or {}
            session.state = "greeting"
            
            # Generate AI greeting
            greeting_response = await self.openai.generate_ai_host_response(
                user_input="User just logged in",
                conversation_state="greeting", 
                user_context=user_context
            )
            
            # Add greeting to conversation history
            session.conversation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": "ai_host",
                "message": greeting_response["response_text"],
                "state": "greeting"
            })
            
            # Store session
            self.active_sessions[session.session_id] = session
            await self._persist_session(session)
            
            logger.info(f"✅ AI host session created: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Failed to start AI host session: {e}")
            raise Exception(f"Failed to start AI host session: {str(e)}")

    async def process_user_input(
        self, 
        session_id: str, 
        user_input: str, 
        audio_file: bytes = None
    ) -> Dict[str, Any]:
        """
        Process user input and generate AI host response
        
        Args:
            session_id: AI host session ID
            user_input: User's text input
            audio_file: Optional audio file for STT processing
            
        Returns:
            AI response with TTS audio, text, and session updates
        """
        try:
            logger.info(f"🎙️ Processing user input for session: {session_id}")
            
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            
            # Process audio if provided
            if audio_file:
                # TODO: Implement STT processing
                logger.info("🎤 Audio input received, STT processing would go here")
            
            # Add user input to conversation history
            session.conversation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": "user",
                "message": user_input,
                "state": session.state
            })
            
            # Process based on current state
            response_data = await self._process_by_state(session, user_input)
            
            # Generate TTS audio for AI response
            if response_data.get("response_text"):
                try:
                    audio_bytes = await self.openai.text_to_speech(
                        text=response_data["response_text"],
                        voice=session.tts_voice
                    )
                    response_data["audio_data"] = audio_bytes
                    response_data["audio_format"] = "mp3"
                except Exception as e:
                    logger.error(f"❌ TTS generation failed: {e}")
                    response_data["tts_error"] = str(e)
            
            # Add AI response to conversation history
            session.conversation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": "ai_host",
                "message": response_data["response_text"],
                "state": session.state
            })
            
            # Persist session updates
            await self._persist_session(session)
            
            # Return response with session info
            response_data.update({
                "session_id": session_id,
                "session_state": session.state,
                "extracted_topics": session.extracted_topics,
                "generated_hashtags": session.generated_hashtags,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"✅ User input processed successfully for session: {session_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Failed to process user input: {e}")
            raise Exception(f"Failed to process user input: {str(e)}")

    async def _process_by_state(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """
        Process user input based on current session state
        """
        if session.state == "greeting":
            return await self._handle_greeting_response(session, user_input)
        elif session.state == "topic_inquiry":
            return await self._handle_topic_response(session, user_input)
        elif session.state == "matching":
            return await self._handle_matching_response(session, user_input)
        elif session.state == "hosting":
            return await self._handle_hosting_response(session, user_input)
        else:
            # Default fallback
            return await self._handle_general_response(session, user_input)

    async def _handle_greeting_response(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Handle user response to AI greeting"""
        # Transition to topic inquiry
        session.state = "topic_inquiry"
        
        # Generate topic inquiry response
        response = await self.openai.generate_ai_host_response(
            user_input=user_input,
            conversation_state="topic_inquiry",
            user_context=session.user_context
        )
        
        return response

    async def _handle_topic_response(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Handle user's topic preferences"""
        try:
            # Extract topics and hashtags from user input
            topic_data = await self.openai.extract_topics_and_hashtags(
                text=user_input,
                context=session.user_context
            )
            
            # Update session with extracted topics
            session.extracted_topics = topic_data["main_topics"]
            session.generated_hashtags = topic_data["hashtags"]
            session.user_context.update({
                "current_topic_category": topic_data["category"],
                "sentiment": topic_data["sentiment"],
                "conversation_style": topic_data["conversation_style"]
            })
            
            # Transition to matching
            session.state = "matching"
            
            # Generate matching response
            response = await self.openai.generate_ai_host_response(
                user_input=f"User wants to discuss: {', '.join(session.extracted_topics)}",
                conversation_state="matching",
                user_context=session.user_context
            )
            
            # Add extracted data to response
            response.update({
                "extracted_topics": session.extracted_topics,
                "generated_hashtags": session.generated_hashtags,
                "topic_category": topic_data["category"]
            })
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Topic extraction failed: {e}")
            
            # Fallback response
            session.extracted_topics = ["general", "chat"]
            session.generated_hashtags = ["#chat", "#social"]
            session.state = "matching"
            
            return {
                "response_text": "Sounds interesting! Let me help you find someone to chat with!",
                "extracted_topics": session.extracted_topics,
                "generated_hashtags": session.generated_hashtags,
                "error": str(e)
            }

    async def _handle_matching_response(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Handle responses during matching process"""
        # Generate matching update response
        response = await self.openai.generate_ai_host_response(
            user_input=user_input,
            conversation_state="matching",
            user_context=session.user_context
        )
        
        return response

    async def _handle_hosting_response(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Handle responses during conversation hosting"""
        # Generate hosting response
        response = await self.openai.generate_ai_host_response(
            user_input=user_input,
            conversation_state="hosting",
            user_context=session.user_context
        )
        
        return response

    async def _handle_general_response(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Handle general responses"""
        response = await self.openai.generate_ai_host_response(
            user_input=user_input,
            conversation_state=session.state,
            user_context=session.user_context
        )
        
        return response

    async def get_session(self, session_id: str) -> Optional[AIHostSession]:
        """Get AI host session by ID"""
        try:
            # Check in-memory cache first
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Check if session is still valid
                if self._is_session_valid(session):
                    return session
                else:
                    # Remove expired session
                    del self.active_sessions[session_id]
                    await self._remove_session(session_id)
            
            # Try to load from Redis if available
            if self.redis:
                session_data = await self._load_session(session_id)
                if session_data:
                    session = AIHostSession.from_dict(session_data)
                    if self._is_session_valid(session):
                        self.active_sessions[session_id] = session
                        return session
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None

    async def get_active_session(self, user_id: UUID) -> Optional[AIHostSession]:
        """Get active session for a user"""
        try:
            # Search in active sessions
            for session in self.active_sessions.values():
                if session.user_id == user_id and self._is_session_valid(session):
                    return session
            
            # TODO: Search in Redis if needed
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get active session for user {user_id}: {e}")
            return None

    def _is_session_valid(self, session: AIHostSession) -> bool:
        """Check if session is still valid (not expired)"""
        now = datetime.utcnow()
        
        # Check total session timeout
        if now - session.created_at > self.session_timeout:
            return False
        
        # Check idle timeout
        if now - session.last_activity > self.idle_timeout:
            return False
        
        return True

    async def _persist_session(self, session: AIHostSession):
        """Persist session to Redis"""
        try:
            if self.redis:
                session_key = f"ai_session:{session.session_id}"
                session_data = json.dumps(session.to_dict(), ensure_ascii=False)
                await self.redis.set_cache(session_key, session_data, ttl=7200)  # 2 hours
                
        except Exception as e:
            logger.error(f"❌ Failed to persist session: {e}")

    async def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from Redis"""
        try:
            if self.redis:
                session_key = f"ai_session:{session_id}"
                session_data = self.redis.get_cache(session_key)
                if session_data:
                    return json.loads(session_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to load session: {e}")
            return None

    async def _remove_session(self, session_id: str):
        """Remove session from Redis"""
        try:
            if self.redis:
                session_key = f"ai_session:{session_id}"
                self.redis.delete_cache(session_key)
                
        except Exception as e:
            logger.error(f"❌ Failed to remove session: {e}")

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (should be called periodically)"""
        try:
            expired_sessions = []
            for session_id, session in self.active_sessions.items():
                if not self._is_session_valid(session):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                await self._remove_session(session_id)
                
            if expired_sessions:
                logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired AI host sessions")
                
        except Exception as e:
            logger.error(f"❌ Session cleanup failed: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get AI host service statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "session_states": {
                state: sum(1 for s in self.active_sessions.values() if s.state == state)
                for state in ["greeting", "topic_inquiry", "matching", "hosting"]
            },
            "total_conversations": sum(
                len(s.conversation_history) for s in self.active_sessions.values()
            ),
            "timestamp": datetime.utcnow().isoformat()
        } 