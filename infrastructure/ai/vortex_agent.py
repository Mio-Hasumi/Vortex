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
from uuid import UUID

from livekit.agents import (
    Agent, 
    AgentSession, 
    ChatContext, 
    ChatMessage,
    function_tool, 
    RunContext
)
from livekit.agents.llm import LLMError
from livekit.plugins import openai  # Using OpenAI Realtime API for all voice features

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
        chat_ctx: Optional[ChatContext] = None
    ):
        
        # Initialize with personality and instructions
        super().__init__(
            instructions=self._get_agent_instructions(),
            chat_ctx=chat_ctx or ChatContext()
        )
        
        self.openai_service = openai_service
        self.ai_host_service = ai_host_service
        self.room_context = {
            "participants": [],
            "topics": [],
            "conversation_state": "greeting",
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
        self._pending_greeting = None  # Store greeting to be delivered
        
        # Participant tracking
        self.participant_map = {}  # Maps LiveKit identity to user info
        
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

    def _get_agent_instructions(self) -> str:
        """Get the system instructions for Vortex agent"""
        return """You are Vortex, an intelligent AI conversation assistant in a voice chat application. 

IMPORTANT: You operate in PASSIVE LISTENING mode by default. You should only speak when:
1. Someone directly calls you ("Hey Vortex", "Hi Vortex", etc.)
2. Someone uses inappropriate language that needs gentle correction
3. Someone asks for help or suggestions
4. The conversation has been quiet for too long (you'll be notified)

When you DO respond:
- Be warm, friendly, and genuinely helpful
- Keep responses concise (1-3 sentences typically) 
- Ask open-ended questions to encourage discussion
- Share relevant insights when appropriate
- Use natural, conversational language
- Focus on facilitating rather than dominating the conversation

Your role is to:
✅ LISTEN: Quietly monitor conversations and learn from the flow
✅ ASSIST: Help when specifically called upon or when intervention is needed
✅ FACILITATE: Suggest topics or ask questions when requested
✅ MODERATE: Gently redirect inappropriate conversations
✅ SUPPORT: Create a comfortable environment for natural conversation

Remember: Less is often more. Let users have their conversations naturally unless they specifically need your help."""

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session"""
        try:
            logger.info("[AGENT] Vortex agent entering room - will greet users first")
            
            # Room context is already set during agent creation, no need for job context
            room_name = self.room_context.get("room_name", "AI Chat Room")
            logger.info(f"[AGENT] Room context available: {room_name}")
            
            # Give users a moment to settle in
            logger.info("[AGENT] Waiting 3 seconds for users to settle...")
            await asyncio.sleep(3)
            
            # ACTIVE introduction first to explain usage
            if self.room_context.get("timeout_explanation", False):
                # Timeout match explanation
                greeting = (
                    "Hi there! I'm Vortex, your AI conversation assistant. "
                    f"{self.room_context.get('topics_context', 'Since no one was immediately interested in the same topics, I randomly connected you two.')} "
                    "I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to join the conversation, suggest topics, or help in any way!"
                )
            else:
                # Regular match with shared interests
                topics_context = self.room_context.get('topics_context', 'You were matched based on shared interests.')
                hashtags = self.room_context.get('hashtags', [])
                
                if hashtags:
                    greeting = (
                        f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                        f"I see you both are interested in {', '.join(hashtags[:3])}{'...' if len(hashtags) > 3 else ''}! "
                        f"I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to suggest topics, answer questions, or help with your conversation. Enjoy chatting!"
                    )
                else:
                    greeting = (
                        f"Hi everyone! I'm Vortex, your AI conversation assistant. "
                        f"{topics_context} "
                        f"I'll be quietly listening from now on - just say 'Hey Vortex' anytime you want me to join in, suggest topics, or help with your conversation!"
                    )
            
            logger.info(f"[AGENT] About to say greeting: {greeting[:100]}...")
            
            # Use proper LiveKit Agents pattern - queue the greeting to be said immediately
            logger.info("[AGENT] Scheduling immediate greeting...")
            
            try:
                # Set a flag for immediate greeting and queue it
                self._pending_greeting = greeting
                self.listening_mode = False  # Temporarily active to deliver greeting
                logger.info("[AGENT] ✅ Greeting queued for immediate delivery!")
            except Exception as greeting_error:
                logger.error(f"[AGENT] ❌ Error queuing greeting: {greeting_error}")
            
            # Will switch to passive listening mode after greeting is delivered
            self.last_user_message_time = datetime.now()
            self.has_been_introduced = True
            
            logger.info("[AGENT] Vortex greeting ready - will switch to passive listening after delivery")
            
        except Exception as e:
            logger.error(f"[AGENT] ❌ ERROR in on_enter: {e}")
            import traceback
            logger.error(f"[AGENT] Traceback: {traceback.format_exc()}")
            # Set the greeting as pending for delivery on first user message
            logger.info("[AGENT] Setting simple fallback greeting as pending")
            self._pending_greeting = "Hi! I'm Vortex, your AI assistant. Say 'Hey Vortex' anytime you need help!"
            self.listening_mode = False  # Will be set to true after greeting delivery
            logger.info("[AGENT] ✅ Fallback greeting queued successfully!")

    async def on_exit(self) -> None:
        """Called when agent is leaving the session"""
        logger.info("[AGENT] Vortex agent exiting room")
        await self.session.say(
            "Thanks for the great conversation everyone! Hope to chat with you again soon.",
            allow_interruptions=False
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Process user input with smart intervention logic"""
        try:
            # Extract user message content and participant info
            user_input = new_message.text_content()
            logger.info(f"[AGENT] ✅ on_user_turn_completed called! User said: '{user_input}'")
            participant_info = self._get_participant_info(new_message)
            
            # Check if we have a pending greeting to deliver FIRST
            if self._pending_greeting:
                logger.info(f"[AGENT] Delivering pending greeting: {self._pending_greeting[:50]}...")
                # Add greeting as system message to be spoken
                turn_ctx.add_message(
                    role="system", 
                    content=f"IMPORTANT: You must say this greeting first, then switch to passive listening mode: '{self._pending_greeting}'"
                )
                # Clear the pending greeting
                self._pending_greeting = None
                # After greeting is delivered, switch to passive mode
                self.listening_mode = True
                self.room_context["conversation_state"] = "listening"
                logger.info("[AGENT] Greeting delivered - now switching to passive listening mode")
                return  # Let the greeting be spoken
            
            # Update participant message count
            participant_info["message_count"] += 1
            
            # Update conversation tracking with proper participant identification
            self.last_user_message_time = datetime.now()
            self.conversation_log.append({
                "timestamp": self.last_user_message_time,
                "content": user_input,
                "participant_identity": participant_info["identity"],
                "participant_name": participant_info["name"],
                "is_ai_host": participant_info.get("is_ai_host", False)
            })
            
            # Keep only recent conversation history (last 20 messages)
            if len(self.conversation_log) > 20:
                self.conversation_log = self.conversation_log[-20:]
            
            # PASSIVE LISTENING: Only respond if specifically triggered
            intervention_type = await self._should_intervene(user_input)
            
            if intervention_type:
                # Agent is being called to participate
                self.listening_mode = False
                self.room_context["conversation_state"] = "active"
                
                # Increment conversation exchange counter
                self.room_context["total_exchanges"] += 1
                
                # Handle specific intervention types - no need for separate introduction since we greet at start
                    
                # Add conversation context for better responses
                if self.ai_host_service:
                    conversation_context = {
                        "room_context": self.room_context,
                        "recent_message": user_input,
                        "total_exchanges": self.room_context["total_exchanges"],
                        "conversation_state": self.room_context["conversation_state"],
                        "conversation_history": self.conversation_log[-5:],  # Last 5 messages
                        "intervention_type": intervention_type
                    }
                    
                    # Add enriched context to the turn with participant awareness
                    if intervention_type == "profanity":
                        turn_ctx.add_message(
                            role="system",
                            content=f"{participant_info['name']} used inappropriate language. Gently redirect the conversation in a positive direction without being preachy. Address them by name."
                        )
                    else:
                        # Build recent speakers summary
                        recent_speakers = {}
                        for msg in conversation_context['conversation_history']:
                            speaker = msg.get('participant_name', 'Someone')
                            recent_speakers[speaker] = recent_speakers.get(speaker, 0) + 1
                        
                        speakers_summary = ", ".join([f"{name} ({count} messages)" for name, count in recent_speakers.items()])
                        
                        turn_ctx.add_message(
                            role="system",
                            content=f"{participant_info['name']} just called you to participate. Recent conversation: {conversation_context['total_exchanges']} exchanges total. Recent speakers: {speakers_summary}. Address {participant_info['name']} by name and respond naturally to their message: '{user_input}'"
                        )
            else:
                # PASSIVE LISTENING: No intervention triggered - DO NOT RESPOND
                logger.info(f"[AGENT] PASSIVE LISTENING: User '{participant_info['name']}' said: '{user_input[:50]}...' - NO intervention needed")
                logger.info("[AGENT] STAYING SILENT - only respond to 'Hey Vortex' or direct calls")
                self.room_context["conversation_state"] = "listening"
                # Critical: Return early without adding any response context
                return
            
            logger.info(f"[AGENT] Processed turn from {participant_info['name']} ({participant_info['identity']}) - intervention: {intervention_type or 'none'}")
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error in on_user_turn_completed: {e}")
            import traceback
            logger.error(f"[AGENT ERROR] Traceback: {traceback.format_exc()}")

    def _get_participant_info(self, message: ChatMessage) -> Dict[str, Any]:
        """
        Extract participant information from ChatMessage
        
        Based on LiveKit documentation, participant identity should be available
        through the message or session context.
        """
        try:
            # Try to get participant identity from the message
            # ChatMessage should have participant information
            participant_identity = getattr(message, 'participant_identity', None) or getattr(message, 'identity', None)
            
            if not participant_identity:
                # Fallback: try alternative message attributes
                try:
                    # Try different possible attributes for participant identity
                    for attr in ['sender_identity', 'user_identity', 'from_identity', 'speaker_identity']:
                        if hasattr(message, attr):
                            participant_identity = getattr(message, attr)
                            if participant_identity:
                                logger.info(f"[AGENT] Found participant identity via {attr}: {participant_identity}")
                                break
                except Exception as e:
                    logger.warning(f"[AGENT] Error trying alternative participant attributes: {e}")
            
            if not participant_identity:
                # Last resort: generate unknown participant ID
                participant_identity = f"unknown_participant_{len(self.participant_map)}"
                logger.warning(f"[AGENT] Could not determine participant identity, using: {participant_identity}")
            
            # Check if we have cached participant info
            if participant_identity in self.participant_map:
                return self.participant_map[participant_identity]
            
            # Create new participant info
            participant_info = {
                "identity": participant_identity,
                "name": self._get_display_name(participant_identity),
                "is_ai_host": participant_identity.startswith("ai_host_"),
                "join_time": datetime.now(),
                "message_count": 0
            }
            
            # Cache participant info
            self.participant_map[participant_identity] = participant_info
            logger.info(f"[AGENT] New participant registered: {participant_identity} -> {participant_info['name']}")
            
            return participant_info
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error getting participant info: {e}")
            # Fallback participant info
            return {
                "identity": "unknown_participant",
                "name": "Someone",
                "is_ai_host": False,
                "join_time": datetime.now(),
                "message_count": 0
            }

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
        1. "Hey Vortex" is mentioned
        2. Profanity/bad language is detected
        3. Help requests are made
        4. Room is being too quiet
        
        Args:
            user_input: User's message content
            
        Returns:
            Intervention type string or None if should stay passive
        """
        try:
            user_input_lower = user_input.lower()
            logger.info(f"[AGENT] Checking intervention triggers for: '{user_input_lower}'")
            
            # 1. Direct call to Vortex
            vortex_triggers = ['hey vortex', 'hi vortex', 'hello vortex', 'vortex', '@vortex']
            for trigger in vortex_triggers:
                if trigger in user_input_lower:
                    logger.info(f"[AGENT] ✅ Intervention triggered: Direct call detected ('{trigger}')")
                    return "direct_call"
            
            # 2. Profanity detection
            words = re.findall(r'\b\w+\b', user_input_lower)
            for word in words:
                if word in self.profanity_words:
                    logger.info(f"[AGENT] Intervention triggered: Profanity detected ('{word}')")
                    return "profanity"
            
            # 3. Questions or requests for help (secondary triggers)
            help_triggers = ['help', 'what should we', 'what can we', 'suggest', 'ideas', 'topics']
            for trigger in help_triggers:
                if trigger in user_input_lower:
                    logger.info(f"[AGENT] Intervention triggered: Help request detected ('{trigger}')")
                    return "help_request"
            
            # Stay passive for normal conversation
            logger.info(f"[AGENT] No intervention needed for: '{user_input_lower}' - staying passive")
            return None
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error checking intervention triggers: {e}")
            return None

    async def check_silence_intervention(self) -> None:
        """
        Background task to check for silence and intervene if conversation is too quiet
        This should be called periodically
        """
        try:
            if not self.last_user_message_time:
                return
            
            silence_duration = (datetime.now() - self.last_user_message_time).total_seconds()
            
            if silence_duration > self.silence_threshold:
                logger.info(f"[AGENT] Silence intervention triggered: {silence_duration:.1f}s of quiet")
                
                # Get participant names for personalized message
                participant_names = [info["name"] for info in self.participant_map.values() if not info.get("is_ai_host", False)]
                
                if len(participant_names) == 2:
                    greeting = f"Hey {participant_names[0]} and {participant_names[1]}, I noticed things got a bit quiet. Would you like me to suggest something to talk about?"
                elif len(participant_names) == 1:
                    greeting = f"Hey {participant_names[0]}, I noticed things got quiet. Would you like me to suggest a topic to get the conversation going?"
                else:
                    greeting = "I couldn't help but notice things got a bit quiet. Would you like me to suggest something to talk about?"
                
                await self.session.say(greeting, allow_interruptions=True)
                
                # Reset the timer
                self.last_user_message_time = datetime.now()
                self.room_context["conversation_state"] = "active"
                
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error in silence intervention: {e}")

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
            
            await self.session.say(greeting, allow_interruptions=True)
            return f"Introduction provided to {caller_name or 'participants'}: {reason}"
            
        except Exception as e:
            logger.error(f"[AGENT ERROR] ❌ Error in introduction: {e}")
            fallback_greeting = f"Hi {caller_name}! " if caller_name else "Hi! "
            fallback_greeting += "I'm Vortex, your AI conversation assistant. I'm here to help with your conversation - just let me know what you'd like to talk about!"
            
            await self.session.say(fallback_greeting, allow_interruptions=True)
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
            logger.info(f"[AGENT] Suggesting topic in category: {topic_category} for reason: {reason}")
            
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
            return f"Topic suggested: {suggested_topic}"
            
        except Exception as e:
            logger.error(f"❌ Error suggesting topic: {e}")
            return "Let me think of something interesting to discuss..."

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



    async def handle_silence(self, silence_duration: float):
        """Handle periods of silence in the conversation"""
        if silence_duration > self.personality["intervention_threshold"]:
            logger.info(f"[SILENCE] Handling {silence_duration}s of silence")
            
            # Suggest a topic or ask a question
            await self.suggest_conversation_topic(
                context=None,  # We'll handle this differently in silence
                reason=f"silence lasted {silence_duration} seconds"
            )


def create_vortex_agent_session(
    openai_service: OpenAIService,
    ai_host_service: Optional[AIHostService] = None,
    room_context: Dict[str, Any] = None
) -> Tuple[Any, VortexAgent]:
    """
    Create a VortexAgent session using LiveKit Agents framework
    
    Returns the VortexAgent instance that will be used with session.start()
    
    Args:
        openai_service: OpenAI service for LLM functionality
        ai_host_service: AI host service for conversation management
        room_context: Context about the room and participants
        
    Returns:
        Tuple of (None, VortexAgent) - the VortexAgent is ready to use with session.start()
    """
    
    try:
        logger.info("[SESSION DEBUG] Starting VortexAgent creation with LiveKit Agents framework")
        logger.info(f"[SESSION DEBUG] OpenAI service provided: {openai_service is not None}")
        logger.info(f"[SESSION DEBUG] AI host service provided: {ai_host_service is not None}")
        logger.info(f"[SESSION DEBUG] Room context provided: {room_context is not None}")
        
        # Create the agent instance
        logger.info("[SESSION DEBUG] Creating VortexAgent instance...")
        vortex_agent = VortexAgent(
            openai_service=openai_service,
            ai_host_service=ai_host_service
        )
        logger.info("[SESSION DEBUG] ✅ VortexAgent instance created")
        
        # Update room context if provided
        logger.info("[SESSION DEBUG] Updating room context...")
        if room_context:
            logger.info(f"[SESSION DEBUG] Room context details: {room_context}")
            vortex_agent.update_room_context(
                participants=room_context.get("participants", []),
                topics=room_context.get("topics", []),
                settings=room_context.get("room_settings", {})  # Pass the settings from room context
            )
            logger.info("[SESSION DEBUG] ✅ Room context updated")
        else:
            logger.info("[SESSION DEBUG] No room context to update")
        
        logger.info("[SESSION DEBUG] ✅ VortexAgent creation completed successfully")
        # Return None as session (will be created by the framework), and the agent
        return None, vortex_agent
        
    except Exception as e:
        logger.error(f"[SESSION ERROR] ❌ Failed to create VortexAgent: {e}")
        logger.error(f"[SESSION ERROR] ❌ Error type: {type(e)}")
        import traceback
        logger.error(f"[SESSION ERROR] ❌ Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create VortexAgent: {str(e)}") 