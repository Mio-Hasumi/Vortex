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
        
        # Initialize with personality and instructions - use standard Agent constructor
        super().__init__(
            instructions=self._get_agent_instructions(),
            chat_ctx=chat_ctx or ChatContext()
        )
        
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
        
        # Agent personality settings
        self.personality = {
            "name": "Vortex",
            "style": "friendly",
            "engagement_level": 8,  # 1-10 scale
            "intervention_threshold": 15  # seconds of silence before suggesting topics
        }
        
        # Conversation monitoring
        self.conversation_log = []
        self.last_user_message_time = None
        self.silence_threshold = 20  # seconds before considering it "too quiet"
        self.listening_mode = True  # Start in passive listening mode
        self.has_been_introduced = False  # Track if agent has introduced itself
        self.has_greeted = False  # Track if initial greeting has been delivered
        
        # Participant tracking (will be managed externally now)
        self.participant_map = {}  # Maps LiveKit identity to user info
        
        # Greeting message
        self._greeting_message = "Hi everyone! I'm Vortex, your AI conversation assistant. I'm here to help facilitate your discussion and provide assistance when needed. Feel free to continue your conversation!"
        
        # Background tasks
        self._silence_task: Optional[asyncio.Task] = None
        
        # Profanity filter (basic words - can be expanded)
        self.profanity_words = {
            'fuck', 'shit', 'bitch', 'damn', 'ass', 'bastard', 'hell',
            'crap', 'piss', 'whore', 'slut', 'dickhead', 'asshole'
        }
        
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
                
                # Update personality based on settings
                self.personality.update({
                    "engagement_level": settings.get("engagement_level", 8),
                    "style": settings.get("personality", "friendly"),
                })
                
                # Update intervention thresholds
                if settings.get("engagement_level"):
                    # Higher engagement = more likely to intervene
                    engagement = settings["engagement_level"]
                    self.silence_threshold = max(15, 30 - (engagement * 2))  # 15-30 seconds
                    
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

    def set_listening_mode(self, listening: bool):
        """Set the agent's listening mode (called from entrypoint after greeting)"""
        self.listening_mode = listening
        self.room_context["conversation_state"] = "listening" if listening else "active"
        logger.info(f"[AGENT] Listening mode set to: {listening}")
    
    def get_greeting_message(self) -> str:
        """Get the prepared greeting message for entrypoint to deliver"""
        if hasattr(self, '_greeting_message') and self._greeting_message:
            return self._greeting_message
        else:
            # Fallback greeting if on_enter hasn't run yet
            return "Hi everyone! I'm Vortex, your AI conversation assistant. I'm here to help facilitate your discussion and provide assistance when needed. Feel free to continue your conversation!"
    
    def mark_greeting_delivered(self):
        """Mark that the greeting has been delivered by entrypoint"""
        self.has_greeted = True
        self.has_been_introduced = True
        self.last_user_message_time = datetime.now()
        logger.info("[AGENT] ✅ Greeting marked as delivered")

    def _get_agent_instructions(self) -> str:
        """Get dynamic system instructions for Vortex agent with participant context"""
        
        # Get current participant information
        participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
        participant_count = len(participant_names)
        
        # Build participant context
        if participant_count == 2:
            participant_context = f"CONVERSATION CONTEXT: You are facilitating a conversation between TWO PEOPLE: {participant_names[0]} and {participant_names[1]}. When you respond, be aware that both participants can hear you and may want to engage."
        elif participant_count == 1:
            participant_context = f"CONVERSATION CONTEXT: You are currently with ONE PERSON: {participant_names[0]}. Another person may join soon."
        elif participant_count > 2:
            participant_context = f"CONVERSATION CONTEXT: You are facilitating a GROUP conversation with {participant_count} people: {', '.join(participant_names)}. Be inclusive of all participants."
        else:
            participant_context = "CONVERSATION CONTEXT: You are in a voice chat room. People will join and you should facilitate their conversation."
            
        topics_context = ""
        if self.room_context.get("hashtags"):
            hashtags = self.room_context["hashtags"][:3]  # Show up to 3 main topics
            topics_context = f"\nSHARED INTERESTS: The participants were matched based on shared interests in: {', '.join(hashtags)}. You can reference these topics when appropriate."
        
        return f"""You are Vortex, an intelligent AI conversation assistant in a voice chat application.

{participant_context}{topics_context}

IMPORTANT: You operate in PASSIVE LISTENING mode by default. You should only speak when:
1. Someone directly calls you ("Hey Vortex", "Hi Vortex", etc.)  
2. Someone uses inappropriate language that needs gentle correction
3. Someone asks for help or suggestions
4. The conversation has been quiet for too long (you'll be notified)

When you DO respond:
- Be warm, friendly, and genuinely helpful
- Keep responses concise (1-3 sentences typically)
- Address both participants when there are multiple people
- Ask open-ended questions to encourage discussion between participants  
- Share relevant insights when appropriate
- Use natural, conversational language
- Focus on facilitating rather than dominating the conversation

Your role is to:
✅ LISTEN: Quietly monitor conversations and learn from the flow
✅ ASSIST: Help when specifically called upon or when intervention is needed
✅ FACILITATE: Suggest topics or ask questions when requested, encouraging interaction between participants
✅ MODERATE: Gently redirect inappropriate conversations  
✅ SUPPORT: Create a comfortable environment for natural conversation between the participants

Remember: Less is often more. Let participants have their conversations naturally unless they specifically need your help. When there are multiple people, encourage them to talk with each other, not just with you."""

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session"""
        try:
            logger.info("[AGENT] 🎯 Vortex agent entering room - checking for existing users")
            
            # Room context is already set during agent creation
            room_name = self.room_context.get("room_name", "AI Chat Room")
            logger.info(f"[AGENT] Room context available: {room_name}")
            
            # Set up greeting message
            if self.room_context.get("timeout_explanation", False):
                # Timeout match explanation
                self._greeting_message = (
                    "Hi there! I'm Vortex, your AI conversation assistant. "
                    f"{self.room_context.get('topics_context', 'Since no one was immediately interested in the same topics, I randomly connected you two.')} "
                    "I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to join the conversation, suggest topics, or help in any way!"
                )
            else:
                # Regular match with shared interests
                topics_context = self.room_context.get('topics_context', 'You were matched based on shared interests.')
                hashtags = self.room_context.get('hashtags', [])
                
                if hashtags:
                    self._greeting_message = (
                        f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                        f"I see you both are interested in {', '.join(hashtags[:3])}{'...' if len(hashtags) > 3 else ''}! "
                        f"I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to suggest topics, answer questions, or help with your conversation. Enjoy chatting!"
                    )
                else:
                    self._greeting_message = (
                        f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                        f"{topics_context} "
                        f"I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to join in, suggest topics, or help with your conversation!"
                    )
            
            logger.info(f"[AGENT] ✅ Greeting prepared: {self._greeting_message[:100]}...")
            
            # Set initial state
            self.listening_mode = True  # Start in listening mode
            self.has_been_introduced = False  # Will be set after greeting
            self.has_greeted = False  # Reset greeting flag
            
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
            
            # Start periodic silence monitoring task
            logger.info("[AGENT] 🔄 Starting silence monitoring background task...")
            self._silence_task = asyncio.create_task(self._monitor_silence_background())
            
        except Exception as e:
            logger.error(f"[AGENT] ❌ ERROR in on_enter: {e}")
            import traceback
            logger.error(f"[AGENT] Traceback: {traceback.format_exc()}")
            # Set fallback greeting
            self._greeting_message = "Hi! I'm Vortex, your AI assistant. Say 'Hey Vortex' anytime you need help!"
            self.has_greeted = False
            logger.info("[AGENT] ✅ Fallback greeting prepared")

    async def on_exit(self) -> None:
        """Called when agent is leaving the session"""
        try:
            logger.info("[AGENT] Vortex agent exiting room")
            
            # Cancel background tasks
            if self._silence_task:
                self._silence_task.cancel()
                logger.info("[AGENT] ✅ Silence monitoring task cancelled")
            
            await self.session.say(
                "Thanks for the great conversation everyone! Hope to chat with you again soon.",
                allow_interruptions=False
            )
        except Exception as e:
            logger.error(f"[AGENT ERROR] Error during exit: {e}")

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Process user input with smart intervention logic"""
        try:
            # Extract user message content and participant info
            user_input = new_message.text_content()
            participant_info = self._get_participant_info(new_message)
            
            logger.info(f"[AGENT] 🎙️ User message from {participant_info['name']}: '{user_input[:50]}...'")
            
            # Log conversation
            self.conversation_log.append({
                "timestamp": datetime.now().isoformat(),
                "participant_name": participant_info['name'],
                "participant_identity": participant_info['identity'],
                "message": user_input,
                "is_ai_host": participant_info.get('is_ai_host', False)
            })
            self.last_user_message_time = datetime.now()
            self.room_context["total_exchanges"] += 1
            
            # Update participant message count
            participant_identity = participant_info['identity']
            if participant_identity in self.participant_map:
                self.participant_map[participant_identity]["message_count"] += 1
            
            # Skip AI host messages
            if participant_info.get("is_ai_host", False):
                return
            
            # Single intervention check
            intervention_type = await self._should_intervene(user_input)
            
            if not intervention_type:
                # PASSIVE LISTENING: Stay silent
                logger.info("[AGENT] 🤐 PASSIVE - staying silent")
                return
            
            # 只在白名单里才说 - 严格控制介入条件
            allowed_interventions = {"direct_call", "profanity"}
            if intervention_type not in allowed_interventions:
                logger.info(f"[AGENT] 🚫 Trigger '{intervention_type}' ignored (not in allowed list: {allowed_interventions})")
                return
            
            # ACTIVE MODE: Handle allowed interventions only
            logger.info(f"[AGENT] 🎯 ACTIVE - {intervention_type}")
            self.listening_mode = False
            self.room_context["conversation_state"] = "active"
            
            # Handle different intervention types with manual responses
            if intervention_type == "direct_call":
                # User called "hey vortex" - context-aware response
                participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
                caller_name = participant_info['name']
                
                if len(participant_names) == 2:
                    # Two people - acknowledge both
                    other_name = [name for name in participant_names if name != caller_name][0]
                    response_msg = f"Hi {caller_name} and {other_name}! I'm here to help with your conversation. What can I do for you both?"
                elif len(participant_names) == 1:
                    # One person - but expecting another
                    response_msg = f"Hi {caller_name}! I'm here to help. What can I do for you? Feel free to continue when your conversation partner joins!"
                else:
                    # Multiple people or fallback
                    response_msg = f"Hi everyone! I'm here to help facilitate your conversation. What can I do for you?"
                
                await self.session.say(response_msg, allow_interruptions=True)
                # Schedule return to listening mode after response
                asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            elif intervention_type == "profanity":
                # Handle inappropriate language
                response_msg = f"Hey {participant_info['name']}, let's keep our conversation positive and respectful. What would you like to talk about instead?"
                await self.session.say(response_msg, allow_interruptions=True)
                # Schedule return to listening mode after response
                asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            # 删除了 else 分支 - 不再对其他类型强制响应
            
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

    async def _should_intervene(self, user_input: str) -> str:
        """
        Determine if the agent should actively respond based on intervention triggers
        
        Agent will intervene when:
        1. "Hey Vortex" is mentioned (with robust regex matching)
        2. Profanity/bad language is detected
        3. Help requests are made
        4. Room is being too quiet
        
        Args:
            user_input: User's message content
            
        Returns:
            Intervention type string or None if should stay passive
        """
        try:
            user_input_lower = user_input.lower().strip()
            logger.info(f"[AGENT] 🔍 Checking intervention triggers for: '{user_input_lower}'")
            
            # 1. Direct call to Vortex - ROBUST REGEX MATCHING
            # Handle variations: "hey vortex", "hi, vortex", "hello vortex!", "hey-vortex", etc.
            vortex_patterns = [
                r'\b(hey|hi|hello)\s*[,\-\s]*vortex\b',  # "hey vortex", "hi, vortex", "hello-vortex"
                r'\bvortex\b.*\?',                        # "vortex, can you help?"
                r'@vortex\b',                             # "@vortex"
                r'\bvortex\s*(help|please|can|could)',    # "vortex help", "vortex can you"
            ]
            
            for pattern in vortex_patterns:
                if re.search(pattern, user_input_lower):
                    logger.info(f"[AGENT] ✅ Direct call detected with pattern: '{pattern}'")
                    return "direct_call"
            
            # 2. Profanity detection with better word boundary checking
            words = re.findall(r'\b\w+\b', user_input_lower)
            profanity_found = []
            for word in words:
                # Stem common variations (fucking -> fuck, etc.)
                base_word = word.rstrip('ing').rstrip('ed').rstrip('s')
                if word in self.profanity_words or base_word in self.profanity_words:
                    profanity_found.append(word)
            
            if profanity_found:
                logger.info(f"[AGENT] ⚠️ Profanity detected: {profanity_found}")
                return "profanity"
            
            # 3. Help/suggestion requests - RESTRICTED: must mention vortex explicitly
            help_patterns = [
                r'\bvortex\b.*\b(help|assist|suggest|recommend)\b',
                r'\b(help|assist|suggest|recommend)\b.*\bvortex\b',
                r'\bvortex\b.*\bwhat\s+(should|can|could)\s+(we|I)\b',
                r'\bvortex\b.*\b(ideas?|topics?)\b'
            ]
            
            for pattern in help_patterns:
                if re.search(pattern, user_input_lower):
                    logger.info(f"[AGENT] 🆘 Vortex-specific help request detected with pattern: '{pattern}'")
                    return "help_request"
            
            # Stay passive for normal conversation
            logger.info(f"[AGENT] 🤐 No intervention needed - staying passive")
            return None
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error checking intervention triggers: {e}")
            return None

    # Greeting logic moved to entrypoint level

    async def _monitor_silence_background(self) -> None:
        """
        Background task that runs continuously to monitor conversation silence
        and intervene when appropriate
        """
        logger.info("[SILENCE MONITOR] 👁️ Background silence monitoring started")
        
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Only monitor silence if agent has been introduced and we have users
                if not self.has_been_introduced or not self.last_user_message_time:
                    continue
                
                # Skip if we're not in listening mode (already speaking/active)
                if not self.listening_mode:
                    logger.debug("[SILENCE MONITOR] 🤫 Skipping check - agent active")
                    continue
                
                silence_duration = (datetime.now() - self.last_user_message_time).total_seconds()
                
                # Only intervene if silence exceeds threshold
                if silence_duration > self.silence_threshold:
                    logger.info(f"[SILENCE MONITOR] 📢 Silence intervention triggered: {silence_duration:.1f}s of quiet")
                    await self._handle_silence_intervention(silence_duration)
                    
            except asyncio.CancelledError:
                logger.info("[SILENCE MONITOR] Background silence monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"[SILENCE MONITOR] ❌ Error in background silence monitoring: {e}")
                import traceback
                logger.error(f"[SILENCE MONITOR] Traceback: {traceback.format_exc()}")
                # Continue monitoring despite errors
                continue

    async def _handle_silence_intervention(self, silence_duration: float) -> None:
        """
        Handle silence intervention when conversation has been quiet for too long
        
        Args:
            silence_duration: How long the silence has lasted in seconds
        """
        try:
            # CRITICAL: Only intervene if we're still in listening mode
            # This prevents multiple interventions if another action started
            if not self.listening_mode:
                logger.info("[SILENCE] 🤫 Skipping intervention - agent already active")
                return
                
            logger.info(f"[SILENCE] 🔇 Handling silence intervention: {silence_duration:.1f}s")
            
            # Get participant names for personalized message
            participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
            
            if len(participant_names) == 2:
                silence_message = f"Hey {participant_names[0]} and {participant_names[1]}, I noticed things got a bit quiet. Would you like me to suggest something to talk about?"
            elif len(participant_names) == 1:
                silence_message = f"Hey {participant_names[0]}, I noticed things got quiet. Would you like me to suggest a topic to get the conversation going?"
            else:
                silence_message = "I couldn't help but notice things got a bit quiet. Would you like me to suggest something to talk about?"
            
            # CRITICAL: Switch to active mode BEFORE speaking
            # This prevents other triggers from firing while we're speaking
            self.listening_mode = False
            self.room_context["conversation_state"] = "active"
            logger.info("[SILENCE] 🗣️ Switching to active mode for intervention")
            
            # Deliver silence intervention message (auto_response=False means no conflicts)
            await self.session.say(silence_message, allow_interruptions=True)
            
            # Reset the timer
            self.last_user_message_time = datetime.now()
            
            # Schedule return to listening mode after a delay
            asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            
            logger.info("[SILENCE] ✅ Silence intervention delivered")
            
        except Exception as e:
            logger.error(f"[SILENCE ERROR] ❌ Error handling silence intervention: {e}")
            # Ensure we return to listening mode even on error
            self.listening_mode = True
            self.room_context["conversation_state"] = "listening"

    async def check_silence_intervention(self) -> None:
        """
        Legacy method - silence checking is now handled by background task
        This method is kept for backwards compatibility
        """
        logger.warning("[SILENCE] ⚠️ check_silence_intervention() called - this is now handled by background task")
        pass

    def get_participant_summary(self) -> str:
        """Get a summary of current participants for context"""
        try:
            participants = [info for info in self.participant_map.values() if not info.get("is_ai_host", False)]
            if not participants:
                return "No participants identified yet"
            
            summary_parts = []
            for participant in participants:
                msg_count = participant.get("message_count", 0)
                summary_parts.append(f"{participant['name']} ({msg_count} messages)")
            
            return f"Participants: {', '.join(summary_parts)}"
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error creating participant summary: {e}")
            return "Participant information unavailable"

    @function_tool()
    async def introduce_myself(
        self,
        context: RunContext,
        reason: str = "user_called",
        caller_name: str = None
    ) -> str:
        """
        Provide a context-aware introduction when users call for Vortex
        
        Args:
            reason: Why the introduction is being given
            caller_name: Name of the person who called Vortex
        """
        try:
            # CRITICAL: Only introduce if we're transitioning from listening mode
            # This prevents duplicate introductions if we're already active
            if not self.listening_mode:
                logger.info("[INTRO] 🤫 Skipping introduction - agent already active")
                return "Skipped introduction - agent already active"
                
            # Switch to active mode BEFORE speaking
            self.listening_mode = False
            self.room_context["conversation_state"] = "active"
            logger.info("[INTRO] 🗣️ Switching to active mode for introduction")
            
            # Get list of participant names for personalized greeting
            participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
            
            # Context-aware greeting based on match type
            if self.room_context.get("timeout_explanation", False):
                # Timeout match explanation
                if caller_name:
                    greeting = (
                        f"Hi {caller_name}! I'm Vortex, your AI conversation assistant. "
                        f"{self.room_context.get('topics_context', 'Since no one was immediately interested in the same topics, I randomly connected you two.')} "
                        f"I can help suggest topics to talk about, answer questions, or just facilitate your conversation. What would you like to chat about?"
                    )
                else:
                    greeting = (
                        f"Hi there! I'm Vortex, your AI conversation assistant. "
                        f"{self.room_context.get('topics_context', 'Since no one was immediately interested in the same topics, I randomly connected you two.')} "
                        f"I can help suggest topics to talk about, answer questions, or just facilitate your conversation. What would you like to chat about?"
                    )
            else:
                # Regular match with shared interests
                topics_context = self.room_context.get('topics_context', 'You were matched based on shared interests.')
                hashtags = self.room_context.get('hashtags', [])
                
                if hashtags:
                    if caller_name and len(participant_names) > 1:
                        greeting = (
                            f"Hi {caller_name}! I'm Vortex, your AI conversation assistant. "
                            f"I see you and {', '.join([name for name in participant_names if name != caller_name])} are interested in {', '.join(hashtags[:3])}{'...' if len(hashtags) > 3 else ''}. "
                            f"I can help facilitate your discussion, suggest related topics, or answer questions. What aspect would you like to explore?"
                        )
                    else:
                        greeting = (
                            f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                            f"I see you're interested in {', '.join(hashtags[:3])}{'...' if len(hashtags) > 3 else ''}. "
                            f"I can help facilitate your discussion, suggest related topics, or answer questions. What aspect would you like to explore?"
                        )
                else:
                    if caller_name:
                        greeting = (
                            f"Hi {caller_name}! I'm Vortex, your AI conversation assistant. "
                            f"{topics_context} "
                            f"I can help with topic suggestions, answer questions, or just facilitate your conversation. How can I help?"
                        )
                    else:
                        greeting = (
                            f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                            f"{topics_context} "
                            f"I can help with topic suggestions, answer questions, or just facilitate your conversation. How can I help?"
                        )
            
            # Deliver introduction (auto_response=False means no conflicts)
            await self.session.say(greeting, allow_interruptions=True)
            
            # Mark as introduced
            self.has_been_introduced = True
            self.last_user_message_time = datetime.now()
            
            # Schedule return to listening mode after a delay
            asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            
            return f"Introduction provided to {caller_name or 'participants'}: {reason}"
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error in introduction: {e}")
            
            # Ensure we're in active mode even for fallback
            self.listening_mode = False
            self.room_context["conversation_state"] = "active"
            
            # Use simple fallback greeting
            fallback_greeting = f"Hi {caller_name}! " if caller_name else "Hi! "
            fallback_greeting += "I'm Vortex, your AI conversation assistant. I'm here to help with your conversation - just let me know what you'd like to talk about!"
            
            # Deliver fallback greeting
            await self.session.say(fallback_greeting, allow_interruptions=True)
            self.has_been_introduced = True
            self.last_user_message_time = datetime.now()
            
            asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            
            return f"Fallback introduction provided due to error: {str(e)}"

    @function_tool()
    async def suggest_conversation_topic(
        self, 
        context: RunContext, 
        topic_category: str = "general",
        reason: str = "conversation lull"
    ) -> str:
        """
        Suggest a new conversation topic when the discussion stalls.
        
        Args:
            topic_category: Category of topic to suggest (general, technology, entertainment, etc.)
            reason: Why the topic is being suggested (conversation lull, related to previous topic, etc.)
        """
        try:
            # CRITICAL: Only suggest if we're transitioning from listening mode
            if not self.listening_mode:
                logger.info("[TOPIC] 🤫 Skipping suggestion - agent already active")
                return "Skipped topic suggestion - agent already active"
                
            # Switch to active mode BEFORE speaking
            self.listening_mode = False
            self.room_context["conversation_state"] = "active"
            logger.info("[TOPIC] 🗣️ Switching to active mode for topic suggestion")
            
            logger.info(f"[TOPIC] Suggesting topic in category: {topic_category} for reason: {reason}")
            
            # Use OpenAI service to generate contextual topic suggestions
            if self.openai_service:
                topic_response = await self.openai_service.generate_ai_host_response(
                    user_input=f"Generate a conversation topic for {topic_category} category because of {reason}",
                    conversation_state="hosting",
                    user_context={
                        "room_context": self.room_context,
                        "topic_category": topic_category,
                        "suggestion_reason": reason
                    }
                )
                
                topic_suggestion = topic_response.get("response_text", 
                    "Here's an interesting question: What's something new you've learned recently that surprised you?")
                
                # Deliver topic suggestion
                await self.session.say(topic_suggestion, allow_interruptions=True)
                
                # Schedule return to listening mode
                asyncio.create_task(self._return_to_listening_mode(delay=5.0))
                
                return f"Topic suggested: {topic_suggestion}"
            
            # Fallback topic suggestions
            fallback_topics = {
                "general": "What's something that's been on your mind lately?",
                "technology": "What's the most interesting piece of technology you've used recently?",
                "entertainment": "Have you watched or read anything interesting lately?",
                "personal": "What's something you're excited about right now?",
                "current_events": "What's your take on something interesting happening in the world?"
            }
            
            suggested_topic = fallback_topics.get(topic_category, fallback_topics["general"])
            
            # Deliver fallback topic suggestion
            await self.session.say(suggested_topic, allow_interruptions=True)
            
            # Schedule return to listening mode
            asyncio.create_task(self._return_to_listening_mode(delay=5.0))
            
            return f"Topic suggested: {suggested_topic}"
            
        except Exception as e:
            logger.error(f"❌ Error suggesting topic: {e}")
            
            # Ensure we return to listening mode even on error
            self.listening_mode = True
            self.room_context["conversation_state"] = "listening"
            
            return "Error suggesting topic, returning to listening mode"

    @function_tool()
    async def fact_check_information(
        self, 
        context: RunContext, 
        statement: str, 
        confidence_needed: str = "moderate"
    ) -> str:
        """
        Fact-check information mentioned in conversation.
        
        Args:
            statement: The statement or claim to fact-check
            confidence_needed: Level of confidence needed (low, moderate, high)
        """
        try:
            logger.info(f"🔍 Fact-checking statement: {statement[:100]}...")
            
            if self.openai_service:
                # Use OpenAI to provide fact-checking
                fact_check_response = await self.openai_service.generate_ai_host_response(
                    user_input=f"Fact-check this statement: {statement}",
                    conversation_state="fact_checking",
                    user_context={
                        "statement": statement,
                        "confidence_level": confidence_needed,
                        "context": "friendly conversation"
                    }
                )
                
                return f"Fact-check result: {fact_check_response.get('response_text', 'I could not verify that information.')}"
            
            return "I'd recommend double-checking that information if it's important."
            
        except Exception as e:
            logger.error(f"❌ Error fact-checking: {e}")
            return "I'm not sure about that - what do others think?"

    @function_tool()
    async def encourage_participation(
        self, 
        context: RunContext, 
        participant_type: str = "quiet",
        topic_context: str = "current discussion"
    ) -> str:
        """
        Encourage participation from specific types of participants.
        
        Args:
            participant_type: Type of participant to encourage (quiet, new, disengaged)
            topic_context: Context of current topic to help with engagement
        """
        try:
            logger.info(f"🤝 Encouraging {participant_type} participant in context: {topic_context}")
            
            encouragement_prompts = {
                "quiet": f"I'd love to hear what others think about {topic_context}. Anyone else have thoughts on this?",
                "new": f"For anyone just joining us, we were discussing {topic_context}. What's your take?",
                "disengaged": f"This ties into {topic_context} - I'm curious what everyone's experience has been with this?"
            }
            
            prompt = encouragement_prompts.get(participant_type, encouragement_prompts["quiet"])
            
            # Update room context
            self.room_context["last_encouragement"] = prompt
            
            return f"Encouraged participation: {prompt}"
            
        except Exception as e:
            logger.error(f"❌ Error encouraging participation: {e}")
            return "What does everyone else think about this?"

    @function_tool()
    async def transition_conversation(
        self, 
        context: RunContext, 
        from_topic: str, 
        to_topic: str,
        transition_reason: str = "natural flow"
    ) -> str:
        """
        Smoothly transition from one conversation topic to another.
        
        Args:
            from_topic: Current topic being discussed
            to_topic: New topic to transition to
            transition_reason: Reason for the transition
        """
        try:
            logger.info(f"🔄 Transitioning conversation: {from_topic} -> {to_topic}")
            
            transition_phrases = [
                f"That's really interesting about {from_topic}. Speaking of which, {to_topic}?",
                f"Great discussion on {from_topic}! That reminds me - {to_topic}?",
                f"Thanks for sharing about {from_topic}. On a related note, {to_topic}?",
                f"I love hearing about {from_topic}. Here's something that might interest you all - {to_topic}?"
            ]
            
            # Use AI service to create natural transition if available
            if self.openai_service:
                transition_response = await self.openai_service.generate_ai_host_response(
                    user_input=f"Create a natural conversation transition from {from_topic} to {to_topic}",
                    conversation_state="hosting",
                    user_context={
                        "from_topic": from_topic,
                        "to_topic": to_topic,
                        "reason": transition_reason
                    }
                )
                
                transition_text = transition_response.get("response_text", transition_phrases[0])
                
                # Update room context
                self.room_context["current_topic"] = to_topic
                self.room_context["previous_topic"] = from_topic
                
                return f"Conversation transitioned: {transition_text}"
            
            import random
            return f"Conversation transitioned: {random.choice(transition_phrases)}"
            
        except Exception as e:
            logger.error(f"❌ Error transitioning conversation: {e}")
            return f"That's interesting! Let's also talk about {to_topic}."



    async def _return_to_listening_mode(self, delay: float = 5.0) -> None:
        """
        Helper to return agent to listening mode after a delay
        
        Args:
            delay: Seconds to wait before returning to listening mode
        """
        try:
            await asyncio.sleep(delay)
            
            # Return to listening mode unless we're currently speaking
            if not self.listening_mode:
                self.listening_mode = True
                self.room_context["conversation_state"] = "listening"
                logger.info(f"[MODE] 🎧 Returned to listening mode after {delay}s")
            else:
                logger.info("[MODE] 🤔 Already in listening mode")
                
        except Exception as e:
            logger.error(f"[MODE ERROR] ❌ Error returning to listening mode: {e}")
            # Force return to listening mode on error
            self.listening_mode = True
            self.room_context["conversation_state"] = "listening"
            
    async def handle_silence(self, silence_duration: float):
        """Handle periods of silence in the conversation"""
        if silence_duration > self.personality["intervention_threshold"]:
            logger.info(f"[SILENCE] Handling {silence_duration}s of silence")
            
            # Only suggest topic if we're in listening mode
            if self.listening_mode:
                # Suggest a topic or ask a question
                await self.suggest_conversation_topic(
                    context=None,  # We'll handle this differently in silence
                    reason=f"silence lasted {silence_duration} seconds"
                )


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
        Tuple of (AgentSession, VortexAgent) ready for session.start()
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
        
        # 一体化 Realtime（STT+LLM+TTS）
        rt_llm = realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice="verse",
            temperature=0.7,
            modalities=["audio", "text"],  # 默认音频+文本
            instructions=vortex_agent._get_agent_instructions(),  # Pass participant-aware instructions
            turn_detection=TurnDetection(
                type="server_vad",          # 或 "semantic_vad"
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500,
                create_response=False,      # Still disabled for manual control
                interrupt_response=True,
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