"""
Waiting Room Agent Entrypoint for VoiceApp

This entrypoint deploys the WaitingRoomAgent as a LiveKit agent worker
optimized for waiting room scenarios where users interact with AI while
waiting for matches.

Usage:
    python infrastructure/ai/waiting_room_entrypoint.py start
    python infrastructure/ai/waiting_room_entrypoint.py dev
"""

import asyncio
import logging
import os
from typing import Dict, Any
from uuid import UUID

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli

from .waiting_room_agent import create_waiting_room_agent_session, WaitingRoomAgent
from .openai_service import OpenAIService
from .ai_host_service import AIHostService

logger = logging.getLogger("waiting_room_entrypoint")


async def entrypoint(ctx: JobContext):
    """
    Entrypoint for WaitingRoomAgent deployment
    
    This function is called for each new waiting room session.
    It creates and manages a WaitingRoomAgent instance.
    """
    
    initial_msg = f"🎭 [WAITING_ROOM_ENTRYPOINT] Starting waiting room agent for room: {ctx.room.name}"
    logger.info(initial_msg)
    
    try:
        # Initialize services
        openai_service = get_openai_service()
        if not openai_service:
            logger.error("[WAITING_ROOM_ENTRYPOINT] ❌ OpenAI service not available")
            return
        
        ai_host_service = AIHostService(openai_service=openai_service)
        
        # Extract user context from room metadata
        user_context = extract_user_context_from_room(ctx)
        logger.info(f"[WAITING_ROOM_ENTRYPOINT] User context: {user_context}")
        
        # Connect to room
        await ctx.connect()
        logger.info(f"[WAITING_ROOM_ENTRYPOINT] ✅ Connected to room: {ctx.room.name}")
        
        # Create WaitingRoomAgent session
        session, waiting_room_agent = create_waiting_room_agent_session(
            openai_service=openai_service,
            ai_host_service=ai_host_service,
            user_context=user_context
        )
        logger.info("[WAITING_ROOM_ENTRYPOINT] ✅ WaitingRoomAgent session created")
        
        # Start the agent session
        await session.start(room=ctx.room, agent=waiting_room_agent)
        logger.info("[WAITING_ROOM_ENTRYPOINT] ✅ WaitingRoomAgent started successfully")
        
        # Set up participant event handlers
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"[WAITING_ROOM_ENTRYPOINT] 👤 Participant joined: {participant.identity}")
            # Notify the agent about the participant
            if hasattr(waiting_room_agent, 'notify_participant_joined'):
                try:
                    waiting_room_agent.notify_participant_joined(
                        participant.identity, 
                        {"identity": participant.identity, "name": participant.name or "User"}
                    )
                except Exception as e:
                    logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error notifying agent: {e}")

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"[WAITING_ROOM_ENTRYPOINT] 👋 Participant left: {participant.identity}")
            # Notify the agent about the participant leaving
            if hasattr(waiting_room_agent, 'notify_participant_left'):
                try:
                    waiting_room_agent.notify_participant_left(participant.identity)
                except Exception as e:
                    logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error notifying agent: {e}")
        
        # Monitor session for completion
        await monitor_waiting_room_session(ctx, session, waiting_room_agent, user_context)
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error in entrypoint: {e}")
        import traceback
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] Traceback: {traceback.format_exc()}")
        
        # Send error message to room if possible
        try:
            if ctx.room.local_participant:
                # Note: This would require TTS setup, so we'll just log for now
                logger.error("[WAITING_ROOM_ENTRYPOINT] Would send error message to user")
        except:
            pass


def extract_user_context_from_room(ctx: JobContext) -> Dict[str, Any]:
    """
    Extract user context from room metadata and job information
    
    Args:
        ctx: Job context from LiveKit
        
    Returns:
        User context dictionary for the WaitingRoomAgent
    """
    try:
        import json
        
        # Try to get user info from job metadata
        user_context = {}
        
        if hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            try:
                metadata = json.loads(ctx.job.metadata)
                user_context.update(metadata)
                logger.info(f"[WAITING_ROOM_ENTRYPOINT] Loaded metadata: {list(metadata.keys())}")
            except Exception as e:
                logger.warning(f"[WAITING_ROOM_ENTRYPOINT] Failed to parse job metadata: {e}")
        
        # Try to get info from room metadata
        if hasattr(ctx.room, 'metadata') and ctx.room.metadata:
            try:
                room_metadata = json.loads(ctx.room.metadata)
                user_context.update(room_metadata)
                logger.info(f"[WAITING_ROOM_ENTRYPOINT] Loaded room metadata: {list(room_metadata.keys())}")
            except Exception as e:
                logger.warning(f"[WAITING_ROOM_ENTRYPOINT] Failed to parse room metadata: {e}")
        
        # Set defaults
        default_context = {
            "session_state": "greeting",
            "extracted_topics": [],
            "generated_hashtags": [],
            "conversation_history": [],
            "matching_preferences": {},
            "room_name": ctx.room.name,
            "wait_start_time": agents.datetime.now()
        }
        
        # Merge with defaults
        final_context = {**default_context, **user_context}
        
        logger.info(f"[WAITING_ROOM_ENTRYPOINT] Final context keys: {list(final_context.keys())}")
        return final_context
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error extracting user context: {e}")
        # Return minimal context
        return {
            "session_state": "greeting",
            "extracted_topics": [],
            "generated_hashtags": [],
            "room_name": ctx.room.name if hasattr(ctx, 'room') else "unknown"
        }


async def monitor_waiting_room_session(
    ctx: JobContext, 
    session, 
    waiting_room_agent: WaitingRoomAgent, 
    user_context: Dict[str, Any]
):
    """
    Monitor the waiting room session and handle completion
    
    This function runs in the background and monitors for:
    - Topic extraction completion
    - Matching process initiation
    - User disconnection
    - Session timeout
    """
    logger.info("[WAITING_ROOM_ENTRYPOINT] 🔍 Starting session monitoring")
    
    try:
        # Monitor for up to 30 minutes (waiting room timeout)
        timeout_minutes = 30
        check_interval = 10  # Check every 10 seconds
        
        for i in range(timeout_minutes * 6):  # 30 min * 6 checks per minute
            await asyncio.sleep(check_interval)
            
            # Check if room is still active
            if not ctx.room or len(ctx.room.remote_participants) == 0:
                logger.info("[WAITING_ROOM_ENTRYPOINT] 🚪 No participants left, ending session")
                break
            
            # Get session summary
            try:
                summary = waiting_room_agent.get_session_summary()
                
                # Check if topics have been extracted
                topics = waiting_room_agent.user_context.get("extracted_topics", [])
                if len(topics) >= 2 and not waiting_room_agent.matching_initiated:
                    logger.info(f"[WAITING_ROOM_ENTRYPOINT] 🎯 Topics extracted: {topics}")
                    
                    # Here you could trigger matching process
                    # For now, we'll just log that matching could be initiated
                    logger.info("[WAITING_ROOM_ENTRYPOINT] 🔄 Ready for matching process")
                    waiting_room_agent.matching_initiated = True
                
                # Log session status every minute
                if i % 6 == 0:  # Every 6 checks (1 minute)
                    logger.info(f"[WAITING_ROOM_ENTRYPOINT] 📊 Session status: {summary}")
                    
            except Exception as e:
                logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error in session monitoring: {e}")
        
        logger.info("[WAITING_ROOM_ENTRYPOINT] 🕐 Session monitoring timeout reached")
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Error in session monitoring: {e}")
    finally:
        logger.info("[WAITING_ROOM_ENTRYPOINT] 🏁 Session monitoring ended")


def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance with proper error handling"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("[WAITING_ROOM_ENTRYPOINT] ❌ OPENAI_API_KEY not found in environment")
            return None
        
        base_url = os.getenv("OPENAI_BASE_URL")  # Optional
        
        logger.info("[WAITING_ROOM_ENTRYPOINT] 🎵 Creating OpenAI service...")
        service = OpenAIService(api_key=api_key, base_url=base_url)
        
        logger.info("[WAITING_ROOM_ENTRYPOINT] ✅ OpenAI service created successfully")
        return service
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Failed to create OpenAI service: {e}")
        return None


def prewarm(proc: agents.JobProcess):
    """
    Prewarm function to initialize resources before job execution
    
    This helps reduce cold start times for waiting room sessions.
    """
    logger.info("[WAITING_ROOM_ENTRYPOINT] 🔥 Prewarming waiting room agent resources...")
    
    try:
        # Initialize OpenAI service
        openai_service = get_openai_service()
        if openai_service:
            proc.userdata["openai_service"] = openai_service
            logger.info("[WAITING_ROOM_ENTRYPOINT] ✅ OpenAI service prewarmed")
        else:
            logger.warning("[WAITING_ROOM_ENTRYPOINT] ⚠️ Could not prewarm OpenAI service")
        
        # You could prewarm other resources here
        # e.g., VAD models, TTS models, etc.
        
        logger.info("[WAITING_ROOM_ENTRYPOINT] ✅ Prewarm completed")
        
    except Exception as e:
        logger.error(f"[WAITING_ROOM_ENTRYPOINT] ❌ Prewarm failed: {e}")


if __name__ == "__main__":
    """Run the waiting room agent worker"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Set up worker options
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        # Waiting room specific options
        agent_name="waiting-room-agent",  # For explicit dispatch
        num_idle_processes=1,  # Keep one process warm
        job_memory_limit_mb=1000,  # 1GB limit
        job_memory_warn_mb=500,   # Warn at 500MB
        shutdown_process_timeout=30.0,  # 30s shutdown timeout
        # LiveKit connection settings from environment
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
        ws_url=os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
    )
    
    logger.info("🚀 [WAITING_ROOM_ENTRYPOINT] Starting waiting room agent worker...")
    logger.info(f"🔗 [WAITING_ROOM_ENTRYPOINT] LiveKit URL: {worker_options.ws_url}")
    logger.info(f"🤖 [WAITING_ROOM_ENTRYPOINT] Agent name: {worker_options.agent_name}")
    
    # Run the worker
    cli.run_app(worker_options) 