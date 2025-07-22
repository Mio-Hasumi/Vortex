"""
Vortex Waiting Room Agent - GPT Real-time AI for Pre-Match Conversation

This LiveKit Agent is designed to have a 1-on-1 conversation with a user
to understand their interests before matching them with another user.

Features:
- Engages in natural conversation to discover topics.
- Uses a "tool" to initiate the matching process once topics are confirmed.
- Built on the LiveKit Agents framework for real-time voice interaction.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from livekit.agents import Agent, ChatContext, function_tool, RunContext

from infrastructure.repositories.matching_repository import MatchingRepository
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)

WAITING_ROOM_AGENT_INSTRUCTIONS = """
You are Vortex, a friendly and engaging AI assistant in a voice chat app.

Your primary role is to have a natural conversation with a user to understand what topics they are interested in discussing.

Your conversation flow should be:
1.  **Greeting**: Start with a warm welcome.
2.  **Inquiry**: Ask the user what's on their mind or what they'd like to talk about today.
3.  **Exploration**: Engage with their response. Ask follow-up questions to get more details and clarify their interests. Be curious and enthusiastic.
4.  **Confirmation**: Once you have a good understanding of potential topics, confirm them with the user. For example: "So, it sounds like you're interested in talking about artificial intelligence, startups, and maybe a bit of philosophy. Is that right?"
5.  **Initiate Matching**: Once the user confirms, use the `user_is_ready_to_match` tool to find them a conversation partner. After using the tool, inform the user that you are now looking for someone for them to talk to.
"""


class WaitingRoomAgent(Agent):
    """
    An agent that talks to a user to figure out what they want to chat about,
    and then puts them into the matching queue.
    """

    def __init__(
        self,
        openai_service: OpenAIService,
        chat_ctx: Optional[ChatContext] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            instructions=WAITING_ROOM_AGENT_INSTRUCTIONS,
            chat_ctx=chat_ctx or ChatContext(),
        )
        self.openai_service = openai_service
        self.user_info = user_info or {}
        logger.info("✅ WaitingRoomAgent initialized for user %s", self.user_info.get("id"))

    @function_tool()
    async def user_is_ready_to_match(self, context: RunContext):
        """
        Call this function ONLY when the user has confirmed they are ready to be matched with a conversation partner.
        """
        try:
            from infrastructure.container import container
            # Extract conversation history to analyze for topics
            conversation_text = "\n".join(
                f"{msg.role}: {msg.text_content()}"
                for msg in context.session.chat_ctx.messages
            )

            user_id = str(self.user_info.get("id"))
            logger.info(f"🚀 User '{user_id}' is ready. Analyzing conversation for matching.")

            # Use OpenAI service to extract topics and hashtags from the whole conversation
            topic_data = await self.openai_service.extract_topics_and_hashtags(
                text=conversation_text
            )
            hashtags = topic_data.get("hashtags", [])
            summary = topic_data.get(
                "summary", "User is ready to talk about the discussed topics."
            )

            if not hashtags:
                logger.warning(
                    f"Could not extract hashtags for user {user_id}. Using a fallback."
                )
                await context.session.say(
                    "I'm having a little trouble pinpointing the exact topics. I'll match you on some general interests."
                )
                hashtags = ["#chat", "#general"]

            matching_repo: MatchingRepository = container.get_matching_repository()

            matching_repo.add_to_ai_queue(
                user_id=user_id,
                hashtags=hashtags,
                voice_input=summary,
                ai_session_id=f"ai_waiting_{user_id}_{datetime.utcnow().timestamp()}",
            )

            await context.session.say(
                "Great! I'm now looking for someone for you to talk to. This should only take a moment."
            )

            return {
                "status": "success",
                "message": f"Matching started for user {user_id} with hashtags {hashtags}",
            }
        except Exception as e:
            logger.error(f"❌ Failed to start matching for user {self.user_info.get('id')}: {e}")
            await context.session.say(
                "I seem to be having trouble starting the matching process right now. Please try again in a moment."
            )
            return {"status": "error", "message": str(e)}


def create_waiting_room_agent_session(
    openai_service: OpenAIService, user_info: Dict[str, Any]
) -> Tuple["agents.AgentSession", WaitingRoomAgent]:
    """
    Creates an AgentSession for the WaitingRoomAgent.
    """
    from livekit import agents
    from livekit.plugins import openai
    from openai.types.beta.realtime.session import TurnDetection

    agent = WaitingRoomAgent(openai_service=openai_service, user_info=user_info)

    session = agents.AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice="shimmer",
            temperature=0.8,
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.5,
                silence_duration_ms=600,
                create_response=True,
                interrupt_response=True,
            ),
        ),
        tts=openai.TTS(model="tts-1", voice="nova"),
    )

    return session, agent 