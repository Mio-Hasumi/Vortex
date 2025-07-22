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
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID

from livekit.agents import (
    Agent, 
    AgentSession, 
    ChatContext, 
    ChatMessage,
    function_tool, 
    RunContext,
    get_job_context
)
from livekit.agents.llm import LLMError
from livekit.plugins import openai  # Using OpenAI Realtime API for all voice features
from livekit.plugins.turn_detector.multilingual import MultilingualModel

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
            "total_exchanges": 0
        }
        
        # Agent personality settings
        self.personality = {
            "name": "Vortex",
            "style": "friendly",
            "engagement_level": 8,  # 1-10 scale
            "intervention_threshold": 10  # seconds of silence before suggesting topics
        }
        
        logger.info("✅ VortexAgent initialized with conversation hosting capabilities")

    def _get_agent_instructions(self) -> str:
        """Get the system instructions for Vortex agent"""
        return """You are Vortex, an intelligent AI conversation host in a voice chat application. Your role is to facilitate engaging, natural conversations between participants.

Your key responsibilities:
1. 🎭 HOST: Welcome new participants warmly and help them feel comfortable
2. 🗣️ FACILITATE: Keep conversations flowing by asking thoughtful questions and suggesting topics
3. ✅ FACT-CHECK: When participants mention information, provide friendly verification if needed
4. 🎪 ENGAGE: Suggest interesting topics when conversations naturally pause
5. 🤝 INCLUDE: Ensure all participants have opportunities to contribute
6. ⚖️ MODERATE: Keep discussions positive and respectful

Conversation style:
- Be warm, friendly, and genuinely interested
- Keep responses concise (1-3 sentences typically)
- Ask open-ended questions to encourage discussion
- Share relevant insights when appropriate
- Use natural, conversational language
- Be encouraging and supportive

When conversations stall:
- Suggest related topics or ask follow-up questions
- Share interesting facts or perspectives
- Invite quieter participants to share their thoughts
- Transition to new topics smoothly

Remember: You're a helpful host, not the main speaker. Your goal is to help participants have great conversations with each other."""

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session"""
        logger.info("🎭 Vortex agent entering room as conversation host")
        
        # Update room context
        job_ctx = get_job_context()
        self.room_context["room_name"] = job_ctx.room.name
        
        # Greet participants warmly
        await self.session.say(
            "Hi everyone! I'm Vortex, your AI conversation host. I'm here to help facilitate our discussion and make sure everyone has a great time. What would you all like to talk about today?",
            allow_interruptions=True
        )
        
        # Update conversation state
        self.room_context["conversation_state"] = "active"

    async def on_exit(self) -> None:
        """Called when agent is leaving the session"""
        logger.info("👋 Vortex agent exiting room")
        await self.session.say(
            "Thanks for the great conversation everyone! Hope to chat with you again soon.",
            allow_interruptions=False
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Process user input and update conversation context"""
        try:
            # Increment conversation exchange counter
            self.room_context["total_exchanges"] += 1
            
            # Extract user message content
            user_input = new_message.text_content()
            
            # Add conversation context for better responses
            if self.ai_host_service:
                # Use existing AI service to analyze conversation flow
                conversation_context = {
                    "room_context": self.room_context,
                    "recent_message": user_input,
                    "total_exchanges": self.room_context["total_exchanges"],
                    "conversation_state": self.room_context["conversation_state"]
                }
                
                # Add enriched context to the turn
                turn_ctx.add_message(
                    role="system",
                    content=f"Conversation context: {conversation_context['total_exchanges']} exchanges so far. Current state: {conversation_context['conversation_state']}. Respond as a helpful conversation host."
                )
                
            logger.info(f"📝 Processed user turn: {self.room_context['total_exchanges']} exchanges")
            
        except Exception as e:
            logger.error(f"❌ Error in on_user_turn_completed: {e}")

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
            logger.info(f"💡 Suggesting topic in category: {topic_category} for reason: {reason}")
            
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

    def update_room_context(self, participants: List[str] = None, topics: List[str] = None):
        """Update the room context with current participants and topics"""
        if participants:
            self.room_context["participants"] = participants
            logger.info(f"👥 Updated room participants: {len(participants)} total")
            
        if topics:
            self.room_context["topics"] = topics
            logger.info(f"🏷️ Updated room topics: {topics}")

    async def handle_silence(self, silence_duration: float):
        """Handle periods of silence in the conversation"""
        if silence_duration > self.personality["intervention_threshold"]:
            logger.info(f"🤫 Handling {silence_duration}s of silence")
            
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
    Create a VortexAgent session using OpenAI Realtime API (Official Best Practice)
    
    Uses OpenAI's integrated Realtime API for optimal performance:
    - Built-in STT, LLM, TTS, and VAD
    - Lower latency than separate components
    - Better turn detection and interruption handling
    
    Args:
        openai_service: OpenAI service for LLM functionality
        ai_host_service: AI host service for conversation management
        room_context: Context about the room and participants
        
    Returns:
        Tuple of (AgentSession, VortexAgent) ready for use
    """
    
    try:
        logger.info("🏗️ SESSION DEBUG: Starting VortexAgent session creation with OpenAI Realtime API")
        logger.info(f"🏗️ SESSION DEBUG: OpenAI service provided: {openai_service is not None}")
        logger.info(f"🏗️ SESSION DEBUG: AI host service provided: {ai_host_service is not None}")
        logger.info(f"🏗️ SESSION DEBUG: Room context provided: {room_context is not None}")
        
        # Import OpenAI Realtime components
        logger.info("🏗️ SESSION DEBUG: Importing OpenAI Realtime components...")
        from livekit.plugins import openai
        from openai.types.beta.realtime.session import TurnDetection
        logger.info("🏗️ SESSION DEBUG: ✅ OpenAI imports successful")
        
        # Create the agent instance
        logger.info("🏗️ SESSION DEBUG: Creating VortexAgent instance...")
        vortex_agent = VortexAgent(
            openai_service=openai_service,
            ai_host_service=ai_host_service
        )
        logger.info("🏗️ SESSION DEBUG: ✅ VortexAgent instance created")
        
        # Update room context if provided
        logger.info("🏗️ SESSION DEBUG: Updating room context...")
        if room_context:
            logger.info(f"🏗️ SESSION DEBUG: Room context details: {room_context}")
            vortex_agent.update_room_context(
                participants=room_context.get("participants", []),
                topics=room_context.get("topics", [])
            )
            logger.info("🏗️ SESSION DEBUG: ✅ Room context updated")
        else:
            logger.info("🏗️ SESSION DEBUG: No room context to update")
        
        # Create session with OpenAI Realtime API (OFFICIAL APPROACH)
        # This replaces separate STT + LLM + TTS + VAD components
        logger.info("🏗️ SESSION DEBUG: Creating AgentSession with OpenAI Realtime API...")
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview",  # Latest Realtime model
                voice="shimmer",  # Natural, friendly voice
                temperature=0.8,  # Balanced creativity
                modalities=["text", "audio"],  # Both text and audio support
                turn_detection=TurnDetection(
                    type="server_vad",  # Server-side voice activity detection
                    threshold=0.5,  # Balanced sensitivity 
                    prefix_padding_ms=300,  # Include 300ms before speech
                    silence_duration_ms=500,  # 500ms silence ends turn
                    create_response=True,  # Auto-generate responses
                    interrupt_response=True  # Allow natural interruptions
                )
            )
        )
        logger.info("🏗️ SESSION DEBUG: ✅ AgentSession created successfully")
        
        logger.info("✅ SESSION DEBUG: VortexAgent session creation completed successfully")
        return session, vortex_agent
        
    except Exception as e:
        logger.error(f"❌ SESSION ERROR: Failed to create VortexAgent session: {e}")
        logger.error(f"❌ SESSION ERROR: Error type: {type(e)}")
        import traceback
        logger.error(f"❌ SESSION ERROR: Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create VortexAgent session: {str(e)}") 