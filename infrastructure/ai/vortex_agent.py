"""
VortexAgent - GPT Real-time AI Host for VoiceApp

This is a LiveKit Agents implementation that serves as an intelligent conversation
host and assistant in voice chat rooms. It follows the LiveKit Agents guidelines
for building voice AI applications.

Features:
- Real-time voice conversation using STT-LLM-TTS pipeline
- Intelligent conversation hosting and guidance
- Topic suggestions and fact-checking
- Seamless integration with existing AI services
- Multi-participant room management
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


from livekit.agents import (
    Agent, 
    AgentSession, 
    ChatContext, 
    ChatMessage,
    function_tool, 
    RunContext
)


from .openai_service import OpenAIService
from .ai_host_service import AIHostService

logger = logging.getLogger(__name__)


class VortexAgent(Agent):
    """
    Vortex AI Host Agent
    
    An intelligent conversation host that can:
    - Welcome users and facilitate introductions
    - Suggest conversation topics when discussions stall
    - Provide fact-checking and relevant information
    - Moderate conversation flow and ensure everyone participates
    - Handle conversation transitions and conclusions
    """
    
    def __init__(
        self, 
        openai_service: OpenAIService,
        ai_host_service: Optional[AIHostService] = None,
        chat_ctx: Optional[ChatContext] = None,
        room_context: Optional[Dict[str, Any]] = None
    ):
        
        # Initialize ALL instance variables FIRST before calling super().__init__
        self.openai_service = openai_service
        self.ai_host_service = ai_host_service
        
        # Initialize room context
        self.room_context = room_context or {
            "participants": [],
            "topics": [],
            "conversation_state": "listening",
            "total_exchanges": 0,
            "match_type": "ai_driven",
            "timeout_explanation": False,
            "intervention_mode": "on_demand",
            "topics_context": "General conversation"
        }
        
        # Conversation monitoring
        self.conversation_log = []
        
        # Participant tracking (CRITICAL: initialize before _get_agent_instructions())
        self.participant_map = {}  # Maps LiveKit identity to user info
        
        # Greeting message
        self._greeting_message = "Hi everyone! I'm Vortex, your AI conversation assistant. I'm here to help facilitate your discussion and provide assistance when needed. Feel free to continue your conversation!"
        

        
        # NOW we can safely call super().__init__ with dynamic instructions
        super().__init__(
            instructions=self._get_agent_instructions(),
            chat_ctx=chat_ctx or ChatContext()
        )
        
        logger.info("✅ VortexAgent initialized with conversation hosting capabilities")

    def update_room_context(
        self, 
        participants: List[Dict[str, Any]] = None, 
        topics: List[str] = None,
        settings: Dict[str, Any] = None
    ):
        """
        Update room context and agent settings based on match information
        
        Args:
            participants: List of room participants
            topics: Conversation topics/hashtags
            settings: Custom agent settings from match creation
        """
        try:
            if participants:
                self.room_context["participants"] = participants
            
            if topics:
                self.room_context["topics"] = topics
                
            if settings:
                # Update room context from custom settings
                self.room_context.update({
                    "match_type": settings.get("match_type", "ai_driven"),
                    "timeout_explanation": settings.get("timeout_explanation", False),
                    "intervention_mode": settings.get("intervention_mode", "on_demand"),
                    "topics_context": settings.get("topics_context", "General conversation"),
                    "hashtags": settings.get("hashtags", []),
                    "confidence": settings.get("confidence", 0.5)
                })
                
                # Pre-populate participant map if participant info is available in settings
                if participants:
                    for participant in participants:
                        if isinstance(participant, dict):
                            identity = participant.get("userId", f"user_{participant.get('displayName', 'unknown')}")
                            self.participant_map[identity] = {
                                "identity": identity,
                                "name": participant.get("displayName", "User"),
                                "is_ai_host": participant.get("isAIHost", False),
                                "join_time": datetime.now(),
                                "message_count": 0
                            }
                
                # Settings processed (personality and intervention logic removed in cleanup)
                    
            logger.info(f"[AGENT] Room context updated: match_type={self.room_context.get('match_type')}, timeout={self.room_context.get('timeout_explanation')}")
            logger.info(f"[AGENT] Participants pre-loaded: {list(self.participant_map.keys())}")
                    
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error updating room context: {e}")

    def notify_participant_joined(self, participant_identity: str, participant_info: Optional[Dict] = None):
        """External notification that a participant joined (called from entrypoint)"""
        try:
            if participant_info:
                self.participant_map[participant_identity] = participant_info
            else:
                self.participant_map[participant_identity] = {
                    "identity": participant_identity,
                    "name": self._get_display_name(participant_identity),
                    "is_ai_host": False,
                    "join_time": datetime.now(),
                    "message_count": 0
                }
            logger.info(f"[AGENT] Participant registered: {participant_identity}")
        except Exception as e:
            logger.error(f"[AGENT ERROR] Error registering participant: {e}")

    def notify_participant_left(self, participant_identity: str):
        """External notification that a participant left (called from entrypoint)"""
        try:
            if participant_identity in self.participant_map:
                self.participant_map[participant_identity]["left_time"] = datetime.now()
            logger.info(f"[AGENT] Participant left: {participant_identity}")
        except Exception as e:
            logger.error(f"[AGENT ERROR] Error handling participant leave: {e}")



    def _get_agent_instructions(self) -> str:
        """Get simplified system instructions"""
        # Get current participant info
        participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
        hashtags = self.room_context.get("hashtags", [])
        match_type = "timeout_explanation" if self.room_context.get("timeout_explanation", False) else "normal"
        
        # Build context for prompt
        context_info = f"""Current context:
- participants: {participant_names}
- match_type: {match_type}
- hashtags: {hashtags[:3] if hashtags else []}"""

        return f"""You are Vortex, an AI conversation assistant.

{context_info}

Behavior:
1. Stay SILENT unless users explicitly mention "Vortex" (e.g., "Hey Vortex", "@Vortex").
2. When addressed directly:
   - Be brief (1-3 sentences)
   - Help people talk to each other
   - Ask questions to facilitate discussion
   - Never dominate the conversation
3. Keep responses natural and friendly.
4. For inappropriate content: Gently redirect ("Let's keep things positive!").

Your role is to facilitate, not lead conversations. Stay quiet and let people connect naturally."""

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session"""
        try:
            logger.info("[AGENT] 🎯 Vortex agent entering room")
            
            # Agent initialized and ready
            
            logger.info("[AGENT] ✅ Ready for greeting delivery by entrypoint")
            
            # CRITICAL: Check for existing participants in room
            if hasattr(self.session, 'room') and hasattr(self.session.room, 'remote_participants'):
                logger.info("[AGENT] 🔍 Checking existing room participants...")
                for participant in self.session.room.remote_participants.values():
                    # Skip AI participants
                    identity = getattr(participant, 'identity', None)
                    if not identity:
                        continue
                        
                    is_ai = (
                        getattr(participant, 'is_ai', False) or
                        identity.startswith('ai_host_') or
                        identity.startswith('vortex_') or
                        identity.lower().startswith('agent_')
                    )
                    
                    if not is_ai:
                        logger.info(f"[AGENT] 👤 Found existing human participant: {identity}")
                        self.participant_map[identity] = {
                            "identity": identity,
                            "name": self._get_display_name(identity),
                            "is_ai_host": False,
                            "join_time": datetime.now(),
                            "message_count": 0
                        }
                
                logger.info(f"[AGENT] ✅ Found {len(self.participant_map)} existing human participants")
            else:
                logger.warning("[AGENT] ⚠️ Could not access room participants - will rely on join events")
            
            logger.info("[AGENT] ✅ Agent ready - will only respond when directly addressed")
            
        except Exception as e:
            logger.error(f"[AGENT] ❌ ERROR in on_enter: {e}")
            # Continue despite error

    async def on_exit(self) -> None:
        """Called when agent is leaving the session"""
        try:
            logger.info("[AGENT] Vortex agent exiting room")
            
            await self.session.say(
                "Thanks for the great conversation everyone! Hope to chat with you again soon.",
                allow_interruptions=False
            )
        except Exception as e:
            logger.error(f"[AGENT ERROR] Error during exit: {e}")


    


    def _addressed_to_me(self, txt: str) -> bool:
        """Check if the message is addressed to Vortex"""
        import re
        return re.search(r'\b(hey|hi|hello)?\s*@?\s*vortex\b', txt, re.I) is not None

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Process user input - only respond when explicitly addressed"""
        try:
            user_input = new_message.text_content()
            participant_info = self._get_participant_info(new_message)
            
            # Simple logging
            logger.info(f"[AGENT] 🎙️ User message from {participant_info['name']}: '{user_input[:50]}...'")
            
            # Update conversation log
            self.conversation_log.append({
                "timestamp": datetime.now().isoformat(),
                "participant_name": participant_info['name'],
                "participant_identity": participant_info['identity'],
                "message": user_input,
                "is_ai_host": participant_info.get('is_ai_host', False)
            })
            
            # Skip AI host messages
            if participant_info.get("is_ai_host", False):
                logger.debug("[AGENT] 🤖 Skipping AI host message")
                return
            
            logger.info(f"[AGENT] 💬 User message: '{user_input[:50]}...'")
            
            # Check if message is addressed to Vortex
            if not self._addressed_to_me(user_input):
                logger.info("[AGENT] 🤫 Message not addressed to me - staying silent")
                # 阻止默认回复（不同版本写法不同）
                try:
                    turn_ctx.prevent_default()
                except AttributeError:
                    try:
                        turn_ctx.should_respond = False
                    except AttributeError:
                        logger.debug("[AGENT] Could not prevent default response - relying on prompt control")
                return
            
            logger.info("[AGENT] 🗣️ Message addressed to me - responding")
            
            # Provide a helpful response
            participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
            if len(participant_names) >= 2:
                response = f"Hi! I see {', '.join(participant_names)} here. What can I help you discuss?"
            else:
                response = "Hi! What can I help you with?"
                
            await self.session.say(response)
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error in on_user_turn_completed: {e}")
    

    


    # Participant join/leave handling moved to entrypoint level

    def _get_participant_info(self, message: ChatMessage) -> Dict[str, Any]:
        """
        Extract participant information from ChatMessage with improved identity parsing
        
        Based on LiveKit documentation, participant identity should be available
        through the message or session context.
        """
        try:
            participant_identity = None
            
            # Primary: Try to get participant identity from the message
            identity_attributes = [
                'participant_identity', 'identity', 'sender_identity', 
                'user_identity', 'from_identity', 'speaker_identity'
            ]
            
            for attr in identity_attributes:
                if hasattr(message, attr):
                    participant_identity = getattr(message, attr)
                    if participant_identity and participant_identity.strip():
                        logger.debug(f"[AGENT] Found participant identity via {attr}: {participant_identity}")
                        break
            
            # Fallback: Try to get from session context if available
            if not participant_identity and hasattr(self, 'session') and hasattr(self.session, 'participant'):
                try:
                    participant_identity = self.session.participant.identity
                    logger.debug(f"[AGENT] Found participant identity via session: {participant_identity}")
                except Exception as e:
                    logger.debug(f"[AGENT] Could not get identity from session: {e}")
            
            # Generate stable fallback ID only if absolutely necessary
            if not participant_identity or not participant_identity.strip():
                # Use a more stable fallback based on message timestamp/hash
                fallback_id = f"participant_{hash(str(message) + str(datetime.now().minute)) % 1000}"
                participant_identity = fallback_id
                logger.warning(f"[AGENT] ⚠️ Generated fallback participant ID: {participant_identity}")
            
            # Check if we have cached participant info
            if participant_identity in self.participant_map:
                cached_info = self.participant_map[participant_identity]
                logger.debug(f"[AGENT] Using cached participant info for: {participant_identity}")
                return cached_info
            
            # Create new participant info with better AI host detection
            is_ai_host = (
                participant_identity.startswith("ai_host_") or 
                participant_identity.startswith("vortex_") or
                participant_identity.lower().startswith("agent_")
            )
            
            participant_info = {
                "identity": participant_identity,
                "name": self._get_display_name(participant_identity),
                "is_ai_host": is_ai_host,
                "join_time": datetime.now(),
                "message_count": 0
            }
            
            # Cache participant info
            self.participant_map[participant_identity] = participant_info
            logger.info(f"[AGENT] 👤 New participant registered: {participant_identity} -> {participant_info['name']} (AI: {is_ai_host})")
            
            return participant_info
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error getting participant info: {e}")
            import traceback
            logger.error(f"[AGENT ERROR] Traceback: {traceback.format_exc()}")
            
            # Safe fallback participant info
            fallback_identity = f"error_participant_{datetime.now().microsecond}"
            fallback_info = {
                "identity": fallback_identity,
                "name": "Someone",
                "is_ai_host": False,
                "join_time": datetime.now(),
                "message_count": 0
            }
            # Don't cache error fallbacks to avoid confusion
            return fallback_info

    def _get_display_name(self, identity: str) -> str:
        """
        Convert LiveKit identity to human-readable display name
        
        Based on LiveKit token generation patterns:
        - user_12345 -> User
        - ai_host_67890 -> Vortex (AI)
        - alice_bob -> Alice
        """
        try:
            if identity.startswith("ai_host_"):
                return "Vortex (AI)"
            elif identity.startswith("user_"):
                # Try to get actual name from room context participants
                user_id = identity.replace("user_", "")
                participants = self.room_context.get("participants", [])
                for participant in participants:
                    if participant.get("userId") == user_id:
                        return participant.get("displayName", "User")
                return "User"
            else:
                # Extract name from identity (e.g., "alice_smith" -> "Alice")
                name_part = identity.split("_")[0] if "_" in identity else identity
                return name_part.title()
                
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error getting display name for {identity}: {e}")
            return "Someone"

    # Removed complex intervention logic - now using pure prompt control

    # Greeting logic moved to entrypoint level






















            



def create_vortex_agent_session(
    openai_service: OpenAIService,
    ai_host_service: Optional[AIHostService] = None,
    room_context: Dict[str, Any] = None
) -> Tuple[AgentSession, VortexAgent]:
    """
    Create a VortexAgent session using LiveKit Agents framework
    
    Returns AgentSession and VortexAgent instances for use with framework
    
    Args:
        openai_service: OpenAI service for LLM functionality
        ai_host_service: AI host service for conversation management
        room_context: Context about the room and participants
        
    Returns:
        Tuple of (AgentSession, VortexAgent). Use as:
        session, agent = create_vortex_agent_session(...)
        await session.start(room=ctx.room, agent=agent)
    """
    
    try:
        logger.info("[SESSION DEBUG] Creating VortexAgent session with LiveKit Agents framework")
        
        # Create the agent instance
        vortex_agent = VortexAgent(
            openai_service=openai_service,
            ai_host_service=ai_host_service,
            room_context=room_context
        )
        logger.info("[SESSION DEBUG] ✅ VortexAgent instance created")
        
        # Update room context if provided
        if room_context:
            vortex_agent.update_room_context(
                participants=room_context.get("participants", []),
                topics=room_context.get("topics", []),
                settings=room_context.get("room_settings", {})
            )
            logger.info("[SESSION DEBUG] ✅ Room context updated")
        
        # Create AgentSession with OpenAI Realtime API (end-to-end low latency)
        from livekit.plugins.openai import realtime
        from livekit.plugins import openai
        from openai.types.beta.realtime.session import TurnDetection
        
        # VAD 兜底配置 (优先 WebRTC，避免 silero 导入错误)
        vad = None
        try:
            from livekit.agents.vad.webrtc import WebRTCVAD
            vad = WebRTCVAD()
            logger.info("[SESSION DEBUG] ✅ Using WebRTC VAD")
        except Exception:
            vad = None  # 让 Realtime 自己处理
            logger.info("[SESSION DEBUG] ⚠️ No local VAD - using Realtime built-in turn detection")
        
        # 一体化 Realtime（STT+LLM+TTS）- Pure prompt driven
        rt_llm = realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="verse",
            temperature=0.7,
            modalities=["text", "audio"],
            # instructions 已经在 Agent 基类中设置，这里不重复设置避免冲突
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500,
                create_response=False,      # 关键：不要让服务器自动回复
            ),
        )
        
        # Add TTS model for session.say() calls (separate from Realtime API)
        tts_model = openai.TTS(
            model="tts-1",
            voice="nova",  # Match Realtime API voice style
        )
        
        session = AgentSession(
            llm=rt_llm,
            tts=tts_model,           # For manual session.say() calls
            vad=vad,                 # None 时用 Realtime 内置
        )
        
        logger.info("[SESSION DEBUG] ✅ AgentSession created with OpenAI Realtime API")
        
        # Return session and agent
        return session, vortex_agent
        
    except Exception as e:
        logger.error(f"[SESSION ERROR] ❌ Failed to create VortexAgent session: {e}")
        import traceback
        logger.error(f"[SESSION ERROR] Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create VortexAgent session: {str(e)}") 