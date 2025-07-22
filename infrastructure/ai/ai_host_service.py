"""
AI Host Service for VoiceApp

Manages AI-driven conversation flow:
1. User greeting and topic inquiry  
2. Dynamic topic extraction and hashtag generation
3. Intelligent user matching based on hashtags
4. Conversation hosting and guidance

Updated to use WaitingRoomAgent with OpenAI Realtime API
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import json

from .openai_service import OpenAIService
from .waiting_room_agent import create_waiting_room_agent_session, WaitingRoomAgent

logger = logging.getLogger(__name__)


class AIHostSession:
    """
    Represents an AI host session with a user
    Enhanced to work with WaitingRoomAgent
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
        
        # NEW: WaitingRoomAgent integration
        self.agent_session = None
        self.waiting_room_agent = None

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

    async def cleanup_agent_session(self):
        """Clean up the agent session when done"""
        if self.agent_session:
            try:
                await self.agent_session.aclose()
                logger.info(f"[AI_HOST] Cleaned up agent session for {self.session_id}")
            except Exception as e:
                logger.error(f"[AI_HOST] Failed to cleanup agent session: {e}")
            finally:
                self.agent_session = None
                self.waiting_room_agent = None


class AIHostService:
    """
    AI Host Service for managing conversation flow
    Enhanced to use WaitingRoomAgent with OpenAI Realtime API
    """
    
    def __init__(self, openai_service: OpenAIService, redis_service=None):
        self.openai = openai_service
        self.redis = redis_service
        self.active_sessions: Dict[str, AIHostSession] = {}  # In-memory cache
        
        # Session timeouts
        self.session_timeout = timedelta(hours=2)  # 2 hours max session
        self.idle_timeout = timedelta(minutes=30)   # 30 min idle timeout
        
        logger.info("✅ AI Host Service initialized with WaitingRoomAgent support")

    async def start_waiting_room_session(
        self, 
        user_id: UUID, 
        user_context: Dict[str, Any] = None,
        livekit_room: Any = None
    ) -> AIHostSession:
        """
        Start a new waiting room session using WaitingRoomAgent
        
        Args:
            user_id: User's UUID
            user_context: User profile and preferences
            livekit_room: LiveKit room instance for the agent
            
        Returns:
            AIHostSession with active WaitingRoomAgent
        """
        try:
            logger.info(f"[AI_HOST] 🎭 Starting waiting room session for user: {user_id}")
            
            # Check if user already has an active session
            existing_session = await self.get_active_session(user_id)
            if existing_session and existing_session.agent_session:
                logger.info(f"[AI_HOST] ♻️ Found existing agent session: {existing_session.session_id}")
                return existing_session
            
            # Create new session
            session = AIHostSession(user_id)
            session.user_context = user_context or {}
            session.state = "greeting"
            
            # Prepare context for WaitingRoomAgent
            agent_context = {
                "user_id": str(user_id),
                "session_id": session.session_id,
                "user_name": user_context.get("displayName") if user_context else None,
                "session_state": "greeting",
                "extracted_topics": [],
                "generated_hashtags": [],
                "conversation_history": [],
                "matching_preferences": user_context.get("preferences", {}) if user_context else {},
                "wait_start_time": datetime.now()
            }
            
            # Create WaitingRoomAgent session
            if self.openai:
                logger.info("[AI_HOST] Creating WaitingRoomAgent session...")
                
                agent_session, waiting_room_agent = create_waiting_room_agent_session(
                    openai_service=self.openai,
                    ai_host_service=self,
                    user_context=agent_context
                )
                
                session.agent_session = agent_session
                session.waiting_room_agent = waiting_room_agent
                
                # Start the agent session if we have a room
                if livekit_room:
                    logger.info("[AI_HOST] Starting agent session in LiveKit room")
                    await agent_session.start(
                        room=livekit_room,
                        agent=waiting_room_agent
                    )
                else:
                    logger.info("[AI_HOST] Agent session created, waiting for room connection")
                
                logger.info(f"[AI_HOST] ✅ WaitingRoomAgent session created: {session.session_id}")
            else:
                logger.warning("[AI_HOST] OpenAI service not available, falling back to static responses")
                # Add static greeting to conversation history as fallback
                session.conversation_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "speaker": "ai_host",
                    "message": "Hi! I'm Vortex. What would you like to talk about?",
                    "state": "greeting"
                })
            
            # Store session
            self.active_sessions[session.session_id] = session
            await self._persist_session(session)
            
            logger.info(f"[AI_HOST] ✅ Waiting room session created: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"[AI_HOST] ❌ Failed to start waiting room session: {e}")
            # Clean up any partial session
            if 'session' in locals() and session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]
            raise Exception(f"Failed to start waiting room session: {str(e)}")

    async def start_session(self, user_id: UUID, user_context: Dict[str, Any] = None) -> AIHostSession:
        """
        Legacy method - now redirects to waiting room session
        
        Args:
            user_id: User's UUID
            user_context: User profile and preferences
            
        Returns:
            New AI host session with WaitingRoomAgent
        """
        logger.info(f"[AI_HOST] Legacy start_session called, redirecting to waiting room session")
        return await self.start_waiting_room_session(user_id, user_context)

    async def connect_agent_to_room(self, session_id: str, livekit_room: Any) -> bool:
        """
        Connect an existing agent session to a LiveKit room
        
        Args:
            session_id: AI host session ID
            livekit_room: LiveKit room instance
            
        Returns:
            True if connected successfully
        """
        try:
            session = await self.get_session(session_id)
            if not session or not session.agent_session:
                logger.error(f"[AI_HOST] No agent session found for: {session_id}")
                return False
            
            logger.info(f"[AI_HOST] Connecting agent session to LiveKit room: {session_id}")
            
            await session.agent_session.start(
                room=livekit_room,
                agent=session.waiting_room_agent
            )
            
            logger.info(f"[AI_HOST] ✅ Agent connected to room: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[AI_HOST] ❌ Failed to connect agent to room: {e}")
            return False

    async def get_agent_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the agent session including extracted topics
        
        Args:
            session_id: AI host session ID
            
        Returns:
            Session summary with topics and hashtags
        """
        try:
            session = await self.get_session(session_id)
            if not session or not session.waiting_room_agent:
                return None
            
            # Get summary from the waiting room agent
            agent_summary = session.waiting_room_agent.get_session_summary()
            
            # Combine with session data
            return {
                "session_id": session_id,
                "user_id": str(session.user_id),
                "session_state": session.state,
                "agent_summary": agent_summary,
                "extracted_topics": session.waiting_room_agent.user_context.get("extracted_topics", []),
                "generated_hashtags": session.waiting_room_agent.user_context.get("generated_hashtags", []),
                "matching_ready": len(session.waiting_room_agent.user_context.get("extracted_topics", [])) >= 2,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[AI_HOST] ❌ Failed to get agent session summary: {e}")
            return None

    async def process_user_input(
        self, 
        session_id: str, 
        user_input: str, 
        audio_file: bytes = None
    ) -> Dict[str, Any]:
        """
        Process user input - now handled by WaitingRoomAgent
        
        This method is kept for backward compatibility but the actual processing
        is now handled by the WaitingRoomAgent through the LiveKit Agents framework.
        
        Args:
            session_id: AI host session ID
            user_input: User's text input
            audio_file: Optional audio file for STT processing
            
        Returns:
            AI response with session updates
        """
        try:
            logger.info(f"[AI_HOST] 🎙️ Processing user input for session: {session_id}")
            
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Session not found")
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            
            if session.waiting_room_agent and session.agent_session:
                # The actual processing is handled by the WaitingRoomAgent
                # through the LiveKit Agents framework
                logger.info("[AI_HOST] Input will be processed by WaitingRoomAgent")
                
                # Get current state from agent
                agent_summary = session.waiting_room_agent.get_session_summary()
                
                # Update session data from agent
                session.extracted_topics = session.waiting_room_agent.user_context.get("extracted_topics", [])
                session.generated_hashtags = session.waiting_room_agent.user_context.get("generated_hashtags", [])
                session.state = session.waiting_room_agent.user_context.get("session_state", session.state)
                
                # Persist session updates
                await self._persist_session(session)
                
                return {
                    "response_text": "Processing through WaitingRoomAgent...",
                    "session_id": session_id,
                    "session_state": session.state,
                    "extracted_topics": session.extracted_topics,
                    "generated_hashtags": session.generated_hashtags,
                    "agent_summary": agent_summary,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Fallback to legacy processing
                logger.warning("[AI_HOST] No WaitingRoomAgent available, using legacy processing")
                return await self._legacy_process_user_input(session, user_input)
            
        except Exception as e:
            logger.error(f"[AI_HOST] ❌ Failed to process user input: {e}")
            raise Exception(f"Failed to process user input: {str(e)}")

    async def _legacy_process_user_input(self, session: AIHostSession, user_input: str) -> Dict[str, Any]:
        """Legacy user input processing for backward compatibility"""
        try:
            # Add user input to conversation history
            session.conversation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": "user",
                "message": user_input,
                "state": session.state
            })
            
            # Process based on current state
            response_data = await self._process_by_state(session, user_input)
            
            # Generate TTS audio for AI response if available
            if response_data.get("response_text") and self.openai:
                try:
                    audio_bytes = await self.openai.text_to_speech(
                        text=response_data["response_text"],
                        voice=session.tts_voice
                    )
                    response_data["audio_data"] = audio_bytes
                    response_data["audio_format"] = "mp3"
                except Exception as e:
                    logger.error(f"[AI_HOST] ❌ TTS generation failed: {e}")
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
                "session_id": session.session_id,
                "session_state": session.state,
                "extracted_topics": session.extracted_topics,
                "generated_hashtags": session.generated_hashtags,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return response_data
            
        except Exception as e:
            logger.error(f"[AI_HOST] ❌ Legacy processing failed: {e}")
            return {
                "response_text": "I'm here to help! What would you like to talk about?",
                "session_id": session.session_id,
                "session_state": session.state,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

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