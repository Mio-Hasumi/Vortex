"""
WaitingRoomAgent - GPT Real-time AI Assistant for VoiceApp Waiting Rooms

This is a LiveKit Agents implementation that serves as an intelligent conversation
companion while users wait for matches. It follows the LiveKit Agents guidelines
for building voice AI applications and uses the same patterns as VortexAgent.

Features:
- Real-time voice conversation using OpenAI Realtime API
- Topic extraction and hashtag generation for matching
- User engagement while waiting for matches
- Seamless integration with existing AI services
- Optimized for single-user waiting room scenarios
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


class WaitingRoomAgent(Agent):
    """
    Waiting Room AI Agent
    
    An intelligent conversation companion that helps users while waiting for matches:
    - Welcomes users and explains the matching process
    - Engages in conversation to extract topics and interests
    - Generates hashtags for better matching
    - Provides encouragement and updates during waiting
    - Maintains conversation flow until match is found
    """
    
    def __init__(
        self, 
        openai_service: OpenAIService,
        ai_host_service: Optional[AIHostService] = None,
        chat_ctx: Optional[ChatContext] = None,
        user_context: Optional[Dict[str, Any]] = None
    ):
        
        # Initialize ALL instance variables FIRST before calling super().__init__
        self.openai_service = openai_service
        self.ai_host_service = ai_host_service
        
        # Initialize user context for waiting room
        self.user_context = user_context or {
            "user_id": None,
            "session_state": "greeting",
            "extracted_topics": [],
            "generated_hashtags": [],
            "conversation_history": [],
            "matching_preferences": {},
            "wait_start_time": datetime.now()
        }
        
        # Waiting room specific state
        self.topics_extracted = False
        self.hashtags_generated = False
        self.matching_initiated = False
        
        # Generate dynamic instructions based on context
        system_instructions = self._get_waiting_room_instructions()
        logger.info(f"[WAITING_ROOM] 🎯 Initializing WaitingRoomAgent with instructions ({len(system_instructions)} chars)")
        
        super().__init__(
            instructions=system_instructions,
            chat_ctx=chat_ctx or ChatContext()
        )
        
        logger.info("✅ WaitingRoomAgent initialized for waiting room conversation")

    def _get_waiting_room_instructions(self) -> str:
        """Get instructions optimized for waiting room scenarios"""
        
        session_state = self.user_context.get("session_state", "greeting")
        user_name = self.user_context.get("user_name", "there")
        extracted_topics = self.user_context.get("extracted_topics", [])
        
        base_context = f"""Current context:
- session_state: {session_state}
- user_name: {user_name}
- topics_so_far: {extracted_topics[:3] if extracted_topics else []}"""
        
        logger.info(f"[WAITING_ROOM] 📋 Generating instructions for state: {session_state}")

        if session_state == "greeting":
            return f"""You are Vortex, a friendly AI assistant helping users find conversation partners.

{base_context}

Your role in the GREETING phase:
1. Welcome the user warmly and introduce yourself as Vortex
2. Explain that you'll help them find interesting people to chat with
3. Ask what topics they'd like to discuss today
4. Be conversational, engaging, and encouraging
5. Keep responses brief (1-2 sentences)

IMPORTANT: Always start with English for your first greeting, then adapt to user's language if needed.

Guidelines:
- Be warm and welcoming
- Ask open-ended questions about their interests
- Help them feel comfortable sharing what they want to talk about
- Don't rush - let the conversation flow naturally"""

        elif session_state == "topic_extraction":
            return f"""You are Vortex, helping users identify their conversation interests.

{base_context}

Your role in the TOPIC EXTRACTION phase:
1. Listen carefully to what the user wants to discuss
2. Ask follow-up questions to understand their specific interests
3. Help them articulate topics clearly
4. Guide them toward expressing 3-5 concrete topics
5. Be encouraging and supportive

Guidelines:
- Ask clarifying questions: "What aspects interest you most?"
- Help them be specific: "What about AI fascinates you?"
- Encourage elaboration: "Tell me more about that!"
- Validate their interests: "That sounds fascinating!"
- Keep responses focused on understanding their interests"""

        elif session_state == "matching":
            topics_text = ", ".join(extracted_topics) if extracted_topics else "your interests"
            return f"""You are Vortex, managing the matching process for users.

{base_context}

Your role in the MATCHING phase:
1. Confirm the topics they want to discuss: {topics_text}
2. Explain that you're finding compatible conversation partners
3. Provide encouraging updates about the matching process
4. Keep them engaged with light conversation while matching
5. Be positive and reassuring

Guidelines:
- "Great topics! I'm finding someone who shares your interests in {topics_text}"
- "This should just take a moment while I find the perfect match"
- "While we wait, what got you interested in these topics?"
- Maintain optimism about finding good matches
- Keep conversation light but engaging"""

        else:  # fallback
            return f"""You are Vortex, a friendly AI conversation assistant.

{base_context}

Your role:
1. Be helpful and engaging in conversation
2. Help users with whatever they need
3. Maintain a positive, supportive tone
4. Keep responses brief and natural

Always be warm, helpful, and encouraging in your interactions."""

    def update_user_context(self, **updates):
        """Update user context and refresh instructions if needed"""
        old_state = self.user_context.get("session_state")
        self.user_context.update(updates)
        new_state = self.user_context.get("session_state")
        
        # Update instructions if state changed
        if old_state != new_state:
            logger.info(f"[WAITING_ROOM] State changed from {old_state} to {new_state}")
            # Note: In a full implementation, we'd call self.update_instructions()
            # but that method might not be available in all versions
            
        logger.info(f"[WAITING_ROOM] Context updated: {list(updates.keys())}")

    async def on_enter(self) -> None:
        """Called when agent becomes active in the waiting room"""
        try:
            logger.info("[WAITING_ROOM] 🎯 WaitingRoomAgent entering session")
            
            # Record entry time
            self.user_context["session_start_time"] = datetime.now()
            
            # Provide initial greeting
            greeting = self._get_initial_greeting()
            logger.info(f"[WAITING_ROOM] 🗣️ Delivering greeting: '{greeting[:50]}...'")
            
            await self.session.say(
                greeting,
                allow_interruptions=True
            )
            
            # Update state to topic extraction
            self.update_user_context(session_state="topic_extraction")
            
            logger.info("[WAITING_ROOM] ✅ Initial greeting delivered, ready for conversation")
            
        except Exception as e:
            logger.error(f"[WAITING_ROOM] ❌ ERROR in on_enter: {e}")
            # Continue despite error with fallback greeting
            try:
                await self.session.say(
                    "Hi! I'm Vortex. What would you like to talk about today?",
                    allow_interruptions=True
                )
            except:
                pass

    def _get_initial_greeting(self) -> str:
        """Generate appropriate initial greeting based on context"""
        user_name = self.user_context.get("user_name")
        
        if user_name:
            return f"Hi {user_name}! I'm Vortex, your AI conversation assistant. I'm here to help you find interesting people to chat with. What topics would you like to discuss today?"
        else:
            return "Hi there! I'm Vortex, your AI conversation assistant. I'm here to help you find interesting people to chat with. What topics would you like to discuss today?"

    async def on_exit(self) -> None:
        """Called when agent is leaving the waiting room session"""
        try:
            logger.info("[WAITING_ROOM] WaitingRoomAgent exiting session")
            
            # Record exit time and duration
            start_time = self.user_context.get("session_start_time")
            if start_time:
                duration = datetime.now() - start_time
                logger.info(f"[WAITING_ROOM] Session duration: {duration.total_seconds():.1f} seconds")
            
            # Provide exit message based on context
            if self.matching_initiated and self.user_context.get("extracted_topics"):
                await self.session.say(
                    "Great chatting with you! I've found someone perfect for you to talk with. Enjoy your conversation!",
                    allow_interruptions=False
                )
            else:
                await self.session.say(
                    "Thanks for chatting! Hope to help you find great conversations soon!",
                    allow_interruptions=False
                )
                
        except Exception as e:
            logger.error(f"[WAITING_ROOM] ❌ ERROR in on_exit: {e}")

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Process user input and manage waiting room conversation flow"""
        try:
            user_input = new_message.text_content()
            logger.info(f"[WAITING_ROOM] 🎙️ User input: '{user_input[:50]}...'")
            
            # Add to conversation history
            self.user_context["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "speaker": "user",
                "message": user_input,
                "session_state": self.user_context.get("session_state")
            })
            
            # Process based on current session state
            current_state = self.user_context.get("session_state", "greeting")
            
            if current_state == "greeting":
                await self._handle_greeting_response(user_input)
            elif current_state == "topic_extraction":
                await self._handle_topic_extraction(user_input)
            elif current_state == "matching":
                await self._handle_matching_conversation(user_input)
            else:
                await self._handle_general_conversation(user_input)
                
        except Exception as e:
            logger.error(f"[WAITING_ROOM] ❌ Error processing user input: {e}")
            # Provide fallback response
            await self.session.generate_reply(
                instructions="Respond helpfully to the user's message and keep the conversation going."
            )

    async def _handle_greeting_response(self, user_input: str):
        """Handle user's response to the initial greeting"""
        logger.info("[WAITING_ROOM] Handling greeting response")
        
        # Move to topic extraction state
        self.update_user_context(session_state="topic_extraction")
        
        # Generate response that acknowledges their input and asks for topics
        await self.session.generate_reply(
            instructions=f"The user said: '{user_input}'. Acknowledge their response warmly and ask what specific topics they'd like to discuss. Be encouraging and help them think about their interests."
        )

    async def _handle_topic_extraction(self, user_input: str):
        """Handle topic extraction and hashtag generation"""
        logger.info("[WAITING_ROOM] Processing topic extraction")
        
        try:
            # Use OpenAI service to extract topics and generate hashtags
            if self.openai_service:
                logger.info("[WAITING_ROOM] Using OpenAI service for topic extraction")
                
                topic_data = await self.openai_service.extract_topics_and_hashtags(
                    text=user_input,
                    context={
                        "source": "waiting_room",
                        "conversation_history": self.user_context.get("conversation_history", []),
                        "session_state": "topic_extraction"
                    }
                )
                
                # Update context with extracted topics
                extracted_topics = topic_data.get("main_topics", [])
                generated_hashtags = topic_data.get("hashtags", [])
                
                self.user_context["extracted_topics"].extend(extracted_topics)
                self.user_context["generated_hashtags"].extend(generated_hashtags)
                
                # Remove duplicates while preserving order
                self.user_context["extracted_topics"] = list(dict.fromkeys(self.user_context["extracted_topics"]))
                self.user_context["generated_hashtags"] = list(dict.fromkeys(self.user_context["generated_hashtags"]))
                
                logger.info(f"[WAITING_ROOM] Extracted topics: {self.user_context['extracted_topics']}")
                logger.info(f"[WAITING_ROOM] Generated hashtags: {self.user_context['generated_hashtags']}")
                
                # Check if we have enough topics
                if len(self.user_context["extracted_topics"]) >= 2:
                    # Move to matching state
                    self.update_user_context(session_state="matching")
                    self.topics_extracted = True
                    self.hashtags_generated = True
                    
                    topics_text = ", ".join(self.user_context["extracted_topics"])
                    await self.session.generate_reply(
                        instructions=f"Great! The user wants to discuss: {topics_text}. Confirm these topics and explain that you're now finding them someone perfect to chat with. Be encouraging and positive about the matching process."
                    )
                    
                    # Trigger matching process
                    await self._initiate_matching()
                    
                else:
                    # Ask for more topics
                    await self.session.generate_reply(
                        instructions="The user has shared some interests. Ask them about other topics they might want to discuss, or ask them to elaborate on what they've already mentioned. Help them identify 2-3 clear topics for good matching."
                    )
            
            else:
                logger.warning("[WAITING_ROOM] OpenAI service not available, using fallback")
                await self._handle_topic_extraction_fallback(user_input)
                
        except Exception as e:
            logger.error(f"[WAITING_ROOM] ❌ Topic extraction failed: {e}")
            await self._handle_topic_extraction_fallback(user_input)

    async def _handle_topic_extraction_fallback(self, user_input: str):
        """Fallback topic extraction when OpenAI service is unavailable"""
        # Simple keyword-based extraction
        common_topics = ["technology", "business", "sports", "music", "movies", "travel", "food", "art", "science", "books"]
        found_topics = [topic for topic in common_topics if topic.lower() in user_input.lower()]
        
        if found_topics:
            self.user_context["extracted_topics"].extend(found_topics)
            self.user_context["generated_hashtags"].extend([f"#{topic}" for topic in found_topics])
            
        # Move to matching if we have any topics
        if self.user_context["extracted_topics"]:
            self.update_user_context(session_state="matching")
            await self.session.generate_reply(
                instructions="Acknowledge their interests and explain that you're finding them someone to chat with."
            )
            await self._initiate_matching()
        else:
            await self.session.generate_reply(
                instructions="Ask them to tell you more about what they'd like to discuss."
            )

    async def _handle_matching_conversation(self, user_input: str):
        """Handle conversation while matching is in progress"""
        logger.info("[WAITING_ROOM] Handling matching conversation")
        
        # Provide encouraging updates about matching
        await self.session.generate_reply(
            instructions=f"The user said: '{user_input}' while waiting for a match. Respond naturally to their comment while reassuring them that you're still finding them a great conversation partner. Keep them engaged and positive about the matching process."
        )

    async def _handle_general_conversation(self, user_input: str):
        """Handle general conversation in other states"""
        logger.info("[WAITING_ROOM] Handling general conversation")
        
        await self.session.generate_reply(
            instructions=f"The user said: '{user_input}'. Respond naturally and helpfully while maintaining the waiting room conversation context."
        )

    async def _initiate_matching(self):
        """Initiate the matching process with extracted topics"""
        try:
            logger.info("[WAITING_ROOM] Initiating matching process")
            self.matching_initiated = True
            
            # Here you would integrate with your matching service
            # For now, we'll just log the matching data
            matching_data = {
                "user_id": self.user_context.get("user_id"),
                "topics": self.user_context.get("extracted_topics", []),
                "hashtags": self.user_context.get("generated_hashtags", []),
                "session_id": self.user_context.get("session_id"),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"[WAITING_ROOM] Matching data prepared: {matching_data}")
            
            # You could call your matching service here:
            # if self.ai_host_service:
            #     await self.ai_host_service.initiate_matching(matching_data)
            
        except Exception as e:
            logger.error(f"[WAITING_ROOM] ❌ Failed to initiate matching: {e}")

    @function_tool()
    async def get_current_topics(self, context: RunContext) -> List[str]:
        """Get the currently extracted topics for the user"""
        topics = self.user_context.get("extracted_topics", [])
        logger.info(f"[WAITING_ROOM] 🔍 Current topics requested: {topics}")
        return topics

    @function_tool()
    async def get_current_hashtags(self, context: RunContext) -> List[str]:
        """Get the currently generated hashtags for matching"""
        hashtags = self.user_context.get("generated_hashtags", [])
        logger.info(f"[WAITING_ROOM] 🏷️ Current hashtags requested: {hashtags}")
        return hashtags

    @function_tool()
    async def update_session_state(self, context: RunContext, new_state: str) -> str:
        """Update the session state (for debugging or external control)"""
        old_state = self.user_context.get("session_state")
        self.update_user_context(session_state=new_state)
        logger.info(f"[WAITING_ROOM] 🔄 State updated: {old_state} -> {new_state}")
        return f"Session state updated from {old_state} to {new_state}"

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current waiting room session"""
        start_time = self.user_context.get("session_start_time")
        duration = None
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
            
        return {
            "session_state": self.user_context.get("session_state"),
            "topics_extracted": len(self.user_context.get("extracted_topics", [])),
            "hashtags_generated": len(self.user_context.get("generated_hashtags", [])),
            "conversation_turns": len(self.user_context.get("conversation_history", [])),
            "matching_initiated": self.matching_initiated,
            "session_duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }


def create_waiting_room_agent_session(
    openai_service: OpenAIService,
    ai_host_service: Optional[AIHostService] = None,
    user_context: Dict[str, Any] = None
) -> Tuple[AgentSession, WaitingRoomAgent]:
    """
    Create a WaitingRoomAgent session using LiveKit Agents framework
    
    Returns AgentSession and WaitingRoomAgent instances for waiting room use
    
    Args:
        openai_service: OpenAI service for LLM functionality
        ai_host_service: AI host service for conversation management
        user_context: Context about the user and their session
        
    Returns:
        Tuple of (AgentSession, WaitingRoomAgent)
    """
    
    try:
        logger.info("[WAITING_ROOM] Creating WaitingRoomAgent session with LiveKit Agents framework")
        
        # Create the waiting room agent instance
        waiting_room_agent = WaitingRoomAgent(
            openai_service=openai_service,
            ai_host_service=ai_host_service,
            user_context=user_context
        )
        logger.info("[WAITING_ROOM] ✅ WaitingRoomAgent instance created")
        
        # Create AgentSession with OpenAI Realtime API
        from livekit.plugins.openai import realtime
        from livekit.plugins import openai
        from openai.types.beta.realtime.session import TurnDetection
        
        # VAD configuration (prioritize WebRTC, fallback to None)
        vad = None
        try:
            from livekit.agents.vad.webrtc import WebRTCVAD
            vad = WebRTCVAD()
            logger.info("[WAITING_ROOM] ✅ Using WebRTC VAD")
        except Exception:
            vad = None
            logger.info("[WAITING_ROOM] ⚠️ No local VAD - using Realtime built-in turn detection")
        
        # OpenAI Realtime model (STT+LLM+TTS integrated)
        rt_llm = realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice="nova",  # Good for friendly waiting room conversations
            temperature=0.7,
            modalities=["text", "audio"],
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=800,  # Slightly longer for waiting room (less hurried)
                create_response=False,  # Let the agent control responses
            ),
        )
        
        # Add TTS model for session.say() calls
        tts_model = openai.TTS(
            model="tts-1",
            voice="nova",  # Match Realtime API voice
        )
        
        session = AgentSession(
            llm=rt_llm,
            tts=tts_model,
            vad=vad,
        )
        
        logger.info("[WAITING_ROOM] ✅ AgentSession created with OpenAI Realtime API")
        
        return session, waiting_room_agent
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM] ❌ Failed to create WaitingRoomAgent session: {e}")
        import traceback
        logger.error(f"[WAITING_ROOM] Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create WaitingRoomAgent session: {str(e)}") 