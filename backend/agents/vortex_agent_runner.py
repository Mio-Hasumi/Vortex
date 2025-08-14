#!/usr/bin/env python3
"""
Vortex Agent Runner

Entry point script for running the VortexAgent in LiveKit rooms.
This script follows the LiveKit Agents framework patterns for agent deployment.

Usage:
    python vortex_agent_runner.py

Environment Variables Required:
    LIVEKIT_URL - LiveKit server WebSocket URL
    LIVEKIT_API_KEY - LiveKit API key
    LIVEKIT_API_SECRET - LiveKit API secret
    OPENAI_API_KEY - OpenAI API key for Realtime API (STT + LLM + TTS + VAD)
"""

import asyncio
import logging
import os
import signal
from typing import Dict, Any, Set

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli

# Import our VortexAgent implementation
from infrastructure.ai.vortex_agent import VortexAgent, create_vortex_agent_session
from infrastructure.ai.openai_service import OpenAIService
from infrastructure.ai.ai_host_service import AIHostService
from infrastructure.container import container

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VortexAgentWorker:
    """Worker class that manages VortexAgent instances"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Any] = {}
        self.openai_service = None
        self.ai_host_service = None
        logger.info("🤖 VortexAgentWorker initialized")

    def initialize_services(self):
        """Initialize required services"""
        try:
            # Initialize OpenAI service
            self.openai_service = container.get_openai_service()
            
            # Initialize AI host service
            self.ai_host_service = container.get_ai_host_service()
            
            logger.info("✅ Services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            # Create basic services if container fails
            self.openai_service = OpenAIService()
            self.ai_host_service = None
            logger.warning("⚠️ Using basic services without dependency injection")


# Global worker instance
worker = VortexAgentWorker()


def is_human_participant(participant: rtc.RemoteParticipant) -> bool:
    """Check if participant is a real human (not AI)"""
    return (
        participant.kind == rtc.ParticipantKind.STANDARD and 
        not participant.identity.startswith(('ai_host_', 'vortex_', 'agent_'))
    )


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the VortexAgent
    
    This function handles participant monitoring and greeting at the JobContext level,
    as recommended by LiveKit Agents framework.
    """
    try:
        logger.info(f"🚀 VortexAgent starting job in room: {ctx.room.name}")
        
        # Initialize services if not already done
        if not worker.openai_service:
            worker.initialize_services()
        
        # Extract room context from job metadata if available
        room_context = {}
        expected_users = 2  # Default expected users
        
        if ctx.job.metadata:
            try:
                import json
                metadata = json.loads(ctx.job.metadata)
                room_context = {
                    "participants": metadata.get("participants", []),
                    "topics": metadata.get("topics", ["general discussion"]),
                    "room_type": metadata.get("room_type", "voice_chat"),
                    "created_by": metadata.get("created_by"),
                    "room_settings": metadata.get("room_settings", {})
                }
                expected_users = len(metadata.get("participants", [])) or 2
                logger.info(f"📋 Room context loaded: expected_users={expected_users}")
                
            except json.JSONDecodeError:
                logger.warning("⚠️ Could not parse job metadata as JSON")
        
        # Connect to room first
        await ctx.connect()
        logger.info(f"✅ Connected to LiveKit room: {ctx.room.name}")
        
        # Track humans in room and setup greeting logic
        humans_in_room: Set[str] = set()
        greeting_event = asyncio.Event()
        
        async def on_participant_join(ctx: JobContext, participant: rtc.RemoteParticipant):
            """Handle participant joining"""
            try:
                if not is_human_participant(participant):
                    logger.debug(f"[PARTICIPANT] Skipping non-human participant: {participant.identity}")
                    return
                
                logger.info(f"[PARTICIPANT] Human joined: {participant.identity}")
                humans_in_room.add(participant.identity)
                
                # Notify agent
                vortex_agent = worker.active_sessions[ctx.room.name]["agent"]
                vortex_agent.notify_participant_joined(
                    participant.identity, 
                    {"name": participant.name or participant.identity, "join_time": asyncio.get_event_loop().time()}
                )
                
                # Check if we should greet
                if len(humans_in_room) >= expected_users and not greeting_event.is_set():
                    logger.info(f"[GREETING] 🎉 {len(humans_in_room)} humans joined - triggering greeting!")
                    greeting_event.set()
                    
            except Exception as e:
                logger.error(f"[PARTICIPANT ERROR] Error handling participant join: {e}")
        
        async def on_participant_leave(ctx: JobContext, participant: rtc.RemoteParticipant):
            """Handle participant leaving"""
            try:
                if not is_human_participant(participant):
                    return
                    
                logger.info(f"[PARTICIPANT] Human left: {participant.identity}")
                humans_in_room.discard(participant.identity)
                
                # Notify agent
                vortex_agent = worker.active_sessions[ctx.room.name]["agent"]
                vortex_agent.notify_participant_left(participant.identity)
                    
            except Exception as e:
                logger.error(f"[PARTICIPANT ERROR] Error handling participant leave: {e}")
        
        # Register participant event handlers
        ctx.add_participant_entrypoint(on_participant_join)
        ctx.add_participant_entrypoint(on_participant_leave)
        
        # Check for existing participants
        for participant in ctx.room.remote_participants.values():
            if is_human_participant(participant):
                logger.info(f"[PARTICIPANT] Found existing human: {participant.identity}")
                humans_in_room.add(participant.identity)
        
        logger.info(f"[PARTICIPANT] Initial human count: {len(humans_in_room)}")
        
        # Create VortexAgent session
        session, vortex_agent = create_vortex_agent_session(
            openai_service=worker.openai_service,
            ai_host_service=worker.ai_host_service,
            room_context=room_context
        )
        
        # Store session for cleanup
        worker.active_sessions[ctx.room.name] = {
            "session": session,
            "agent": vortex_agent,
            "context": room_context,
            "humans": humans_in_room
        }
        
        # Start the agent session
        await session.start(
            room=ctx.room,
            agent=vortex_agent
        )
        
        logger.info(f"🎭 VortexAgent active in room: {ctx.room.name}")
        
        # Wait for enough participants to join (if not already present)
        if len(humans_in_room) >= expected_users:
            greeting_event.set()
        
        # Wait for enough participants, then let model handle greeting via prompt
        try:
            await asyncio.wait_for(greeting_event.wait(), timeout=30.0)  # 30 second timeout
            
            logger.info(f"[GREETING] 🎉 {len(humans_in_room)} participants ready - model will greet on next user message")
            logger.info("[GREETING] ✅ Agent ready - waiting for user messages to trigger prompt-based greeting")
            
            # No manual greeting - the model will greet based on its instructions 
            # when ready_to_greet=true and greeted=false in the prompt
            
        except asyncio.TimeoutError:
            logger.warning("[GREETING] ⏰ Greeting timeout - model will still greet when users speak")
            # Still OK - model will greet when conditions are met
        
        # Keep the session running
        logger.info("🎯 VortexAgent session running - waiting for completion")
        
    except Exception as e:
        logger.error(f"❌ VortexAgent job failed: {e}")
        raise


def prewarm(proc: agents.JobProcess):
    """
    Prewarm function to initialize services before jobs start
    
    This improves performance by loading models and services in advance.
    """
    try:
        logger.info("🔥 Prewarming VortexAgent services...")
        
        # Initialize services
        worker.initialize_services()
        
        # Prewarm models if needed
        proc.userdata["openai_service"] = worker.openai_service
        proc.userdata["ai_host_service"] = worker.ai_host_service
        
        logger.info("✅ VortexAgent services prewarmed")
        
    except Exception as e:
        logger.error(f"❌ Prewarming failed: {e}")


async def cleanup_handler():
    """Cleanup active sessions on shutdown"""
    try:
        logger.info("🧹 Cleaning up VortexAgent sessions...")
        
        for room_name, session_data in worker.active_sessions.items():
            try:
                session = session_data["session"]
                await session.aclose()
                logger.info(f"✅ Cleaned up session for room: {room_name}")
                
            except Exception as e:
                logger.error(f"❌ Error cleaning up session for {room_name}: {e}")
        
        worker.active_sessions.clear()
        logger.info("✅ All sessions cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {signum}, initiating shutdown...")
    
    # Run cleanup in the event loop
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cleanup_handler())
    except Exception as e:
        logger.error(f"❌ Error during signal cleanup: {e}")
    
    logger.info("👋 VortexAgent worker shutdown complete")


def check_environment():
    """Check that required environment variables are set"""
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY"
    ]
    
    # No optional API keys needed with OpenAI Realtime API
    optional_vars = []
    
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        logger.error("Please set these environment variables before running the agent")
        return False
    
    # Check optional variables
    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_optional:
        logger.warning(f"⚠️ Missing optional environment variables: {missing_optional}")
        logger.warning("Some features may not work without these variables")
    
    logger.info("✅ Environment check passed")
    return True


def main():
    """Main function to start the VortexAgent worker"""
    
    print("🤖 Starting VortexAgent Worker")
    print("================================")
    
    # Check environment
    if not check_environment():
        exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Log startup info
    logger.info("🤖 VortexAgent Worker starting...")
    logger.info(f"📡 LiveKit URL: {os.getenv('LIVEKIT_URL', 'Not set')}")
    logger.info(f"🔑 OpenAI Realtime API configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    
    # Create worker options
    worker_opts = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm
    )
    
    try:
        # Run the agent worker
        cli.run_app(worker_opts)
        
    except KeyboardInterrupt:
        logger.info("👋 VortexAgent worker interrupted by user")
        
    except Exception as e:
        logger.error(f"❌ VortexAgent worker failed: {e}")
        exit(1)
    
    logger.info("👋 VortexAgent worker stopped")


if __name__ == "__main__":
    main() 