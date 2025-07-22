"""
Agent Manager Service

Manages the deployment and lifecycle of VortexAgents in LiveKit rooms.
This service handles:
- Spawning agents when rooms are created
- Managing agent tokens and permissions
- Coordinating agent behavior with room settings
- Cleaning up agents when rooms are closed
"""

import asyncio
import logging
import json
import subprocess
from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime

from domain.entities import Room
from infrastructure.livekit.livekit_service import LiveKitService
from .openai_service import OpenAIService
from .ai_host_service import AIHostService

logger = logging.getLogger(__name__)


class AgentManagerService:
    """
    Service for managing VortexAgent deployment in LiveKit rooms
    """
    
    def __init__(
        self, 
        livekit_service: LiveKitService,
        openai_service: OpenAIService,
        ai_host_service: AIHostService = None
    ):
        self.livekit = livekit_service
        self.openai_service = openai_service
        self.ai_host_service = ai_host_service
        
        # Track active agents
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        
        # Agent settings
        self.agent_settings = {
            "personality": "friendly",
            "engagement_level": 8,
            "auto_start": True,
            "greeting_enabled": True,
            "fact_checking_enabled": True,
            "topic_suggestions_enabled": True
        }
        
        logger.info("✅ AgentManagerService initialized")

    async def deploy_agent_to_room(
        self, 
        room: Room,
        room_topics: List[str] = None,
        custom_settings: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Deploy a VortexAgent to a specific room
        
        Args:
            room: Room entity to deploy agent to
            room_topics: Topics for the room conversation
            custom_settings: Custom agent settings for this room
            
        Returns:
            Agent deployment information
        """
        try:
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Starting deployment for room: {room.name}")
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Room type: {type(room)}")
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Room attributes: {dir(room)}")
            
            # Generate agent identity (use the existing host_ai_identity)
            agent_identity = room.host_ai_identity
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Agent identity: {agent_identity}")
            
            # Generate agent token with appropriate permissions
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Generating agent token for room: {room.livekit_room_name}")
            agent_token = self.livekit.generate_token(
                room_name=room.livekit_room_name,
                identity=agent_identity,
                can_publish=True,  # Agent needs to speak
                can_subscribe=True,  # Agent needs to hear participants
                can_publish_data=True,  # Agent can send data messages
                ttl=86400  # 24 hours
            )
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Agent token generated successfully (length: {len(agent_token) if agent_token else 'None'})")
            
            # Prepare room context for the agent
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Preparing room context...")
            room_context = {
                "room_id": str(room.id),
                "room_name": room.name,
                "livekit_room_name": room.livekit_room_name,
                "topics": room_topics or ["general discussion"],
                "max_participants": room.max_participants,
                "created_by": str(room.created_by),
                "room_type": "voice_chat",
                "room_settings": custom_settings or self.agent_settings
            }
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Room context prepared: {room_context}")
            
            # Create job metadata for the agent
            job_metadata = {
                "agent_type": "vortex_host",
                "room_context": room_context,
                "deployment_time": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Job metadata prepared: {job_metadata}")
            
            # Deploy agent using LiveKit's agent framework
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Starting agent process for room: {room.livekit_room_name}")
            deployment_result = await self._start_agent_process(
                room_name=room.livekit_room_name,
                agent_token=agent_token,
                metadata=job_metadata
            )
            logger.info(f"🚀 AGENT DEPLOY DEBUG: Agent process result: {deployment_result}")
            
            # Track the deployed agent
            self.active_agents[room.livekit_room_name] = {
                "room_id": str(room.id),
                "agent_identity": agent_identity,
                "agent_token": agent_token,
                "deployment_time": datetime.utcnow(),
                "context": room_context,
                "process_info": deployment_result,
                "status": "active"
            }
            
            logger.info(f"✅ VortexAgent deployed successfully to room: {room.name}")
            
            return {
                "success": True,
                "agent_identity": agent_identity,
                "room_name": room.livekit_room_name,
                "deployment_time": datetime.utcnow().isoformat(),
                "context": room_context
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to deploy agent to room {room.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "room_name": room.name
            }

    async def _start_agent_process(
        self, 
        room_name: str, 
        agent_token: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Start the VortexAgent process for a specific room
        
        This can be implemented in different ways:
        1. Subprocess - spawn a new Python process
        2. Task - run in the same process as an async task
        3. External service - call an external agent service
        """
        
        # For now, we'll use the task-based approach for simplicity
        # In production, you might want to use separate processes or containers
        
        try:
            logger.info(f"🔧 Starting VortexAgent process for room: {room_name}")
            
            # Create a background task that runs the agent
            agent_task = asyncio.create_task(
                self._run_agent_in_room(
                    room_name=room_name,
                    token=agent_token,
                    metadata=metadata
                )
            )
            
            return {
                "method": "async_task",
                "task_id": id(agent_task),
                "room_name": room_name,
                "started_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start agent process: {e}")
            raise

    async def _run_agent_in_room(
        self, 
        room_name: str, 
        token: str, 
        metadata: Dict[str, Any]
    ):
        """
        Run the VortexAgent in a specific room (async task version)
        """
        try:
            logger.info(f"🏃 AGENT RUN DEBUG: Starting VortexAgent in room: {room_name}")
            logger.info(f"🏃 AGENT RUN DEBUG: Token length: {len(token)}")
            logger.info(f"🏃 AGENT RUN DEBUG: Metadata: {metadata}")
            
            # Import here to avoid circular imports
            from .vortex_agent import create_vortex_agent_session
            from livekit.agents import JobContext
            from livekit import rtc
            
            logger.info(f"🏃 AGENT RUN DEBUG: Imports successful")
            
            # Connect to the room using LiveKit SDK
            room_url = self.livekit.server_url
            if room_url.startswith("http"):
                room_url = room_url.replace("http", "ws")
            logger.info(f"🏃 AGENT RUN DEBUG: Connecting to LiveKit at: {room_url}")
            
            # Create a real LiveKit room connection
            room = rtc.Room()
            logger.info(f"🏃 AGENT RUN DEBUG: Room object created")
            
            # Set up room event handlers
            @room.on("participant_connected")
            def on_participant_connected(participant: rtc.RemoteParticipant):
                logger.info(f"🎭 AGENT EVENT: Participant connected: {participant.identity}")
            
            @room.on("participant_disconnected") 
            def on_participant_disconnected(participant: rtc.RemoteParticipant):
                logger.info(f"🎭 AGENT EVENT: Participant disconnected: {participant.identity}")
            
            @room.on("track_published")
            def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                logger.info(f"🎭 AGENT EVENT: Track published by {participant.identity}: {publication.kind}")
            
            logger.info(f"🏃 AGENT RUN DEBUG: Event handlers set up")
            
            # Connect to the room
            logger.info(f"🏃 AGENT RUN DEBUG: Connecting to room with token...")
            await room.connect(room_url, token)
            logger.info(f"🏃 AGENT RUN DEBUG: ✅ Successfully connected to LiveKit room!")
            logger.info(f"🏃 AGENT RUN DEBUG: Room name: {room.name}")
            logger.info(f"🏃 AGENT RUN DEBUG: Local participant: {room.local_participant.identity}")
            
            # Enable microphone for the agent
            logger.info(f"🏃 AGENT RUN DEBUG: Setting up agent audio...")
            try:
                await room.local_participant.set_microphone_enabled(True)
                logger.info(f"🏃 AGENT RUN DEBUG: ✅ Microphone enabled")
            except Exception as mic_error:
                logger.error(f"🏃 AGENT RUN DEBUG: ❌ Microphone setup failed: {mic_error}")
            
            # Create and configure the agent session
            logger.info(f"🏃 AGENT RUN DEBUG: Creating VortexAgent session...")
            session, agent = create_vortex_agent_session(
                openai_service=self.openai_service,
                ai_host_service=self.ai_host_service,
                room_context=metadata.get("room_context", {})
            )
            logger.info(f"🏃 AGENT RUN DEBUG: ✅ VortexAgent session created")
            
            # Start the agent session with the connected room
            logger.info(f"🏃 AGENT RUN DEBUG: Starting agent session...")
            try:
                await session.start(room=room, agent=agent)
                logger.info(f"🏃 AGENT RUN DEBUG: ✅ Agent session started successfully!")
            except Exception as session_error:
                logger.error(f"🏃 AGENT RUN DEBUG: ❌ Agent session start failed: {session_error}")
                import traceback
                logger.error(f"🏃 AGENT RUN DEBUG: Session error traceback: {traceback.format_exc()}")
                # Don't return here, keep the agent running even if session start failed
            
            # Log that the agent is now active
            logger.info(f"🎭 ✅ VortexAgent is now ACTIVE and CONNECTED in room: {room_name}")
            logger.info(f"🎭 ✅ Agent identity: {room.local_participant.identity}")
            logger.info(f"🎭 ✅ Room participants: {[p.identity for p in room.remote_participants]}")
            
            # Keep the agent running
            while room_name in self.active_agents and room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.sleep(5)  # Check every 5 seconds
                logger.info(f"🎭 HEARTBEAT: Agent still active in {room_name}, participants: {len(room.remote_participants)}")
                
                # Check if room still exists
                try:
                    room_info = await self.livekit.get_room_info(room_name)
                    if not room_info:
                        logger.info(f"🏃‍♀️ Room {room_name} no longer exists, stopping agent")
                        break
                except Exception as check_error:
                    logger.warning(f"🏃‍♀️ Error checking room {room_name}: {check_error}")
                    break
            
            logger.info(f"👋 VortexAgent stopping for room: {room_name}")
            
            # Disconnect from room
            try:
                await room.disconnect()
                logger.info(f"👋 VortexAgent disconnected from room: {room_name}")
            except Exception as disconnect_error:
                logger.error(f"❌ Error disconnecting agent: {disconnect_error}")
            
            # Cleanup session resources
            try:
                await session.aclose()
                logger.info(f"🧹 VortexAgent session cleaned up for room: {room_name}")
            except Exception as cleanup_error:
                logger.error(f"❌ Error cleaning up agent session: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"❌ AGENT RUN ERROR: Error running agent in room {room_name}: {e}")
            import traceback
            logger.error(f"❌ AGENT RUN ERROR: Traceback: {traceback.format_exc()}")
            
        finally:
            # Clean up
            if room_name in self.active_agents:
                self.active_agents[room_name]["status"] = "stopped"
                logger.info(f"🧹 Agent status set to stopped for room: {room_name}")

    async def remove_agent_from_room(self, room_name: str) -> Dict[str, Any]:
        """
        Remove VortexAgent from a specific room
        
        Args:
            room_name: LiveKit room name
            
        Returns:
            Removal result information
        """
        try:
            logger.info(f"🗑️ Removing VortexAgent from room: {room_name}")
            
            if room_name not in self.active_agents:
                logger.warning(f"⚠️ No active agent found for room: {room_name}")
                return {
                    "success": True,
                    "message": "No agent was active in this room",
                    "room_name": room_name
                }
            
            # Get agent info
            agent_info = self.active_agents[room_name]
            agent_identity = agent_info["agent_identity"]
            
            # Remove participant from LiveKit room
            try:
                success = self.livekit.remove_participant(room_name, agent_identity)
                if success:
                    logger.info(f"✅ Removed agent participant {agent_identity} from room {room_name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not remove agent participant: {e}")
            
            # Mark agent as stopped
            agent_info["status"] = "stopped" 
            agent_info["stopped_at"] = datetime.utcnow()
            
            # Remove from active agents after a delay (to allow cleanup)
            asyncio.create_task(self._cleanup_agent_after_delay(room_name, delay=10))
            
            logger.info(f"✅ VortexAgent removal initiated for room: {room_name}")
            
            return {
                "success": True,
                "agent_identity": agent_identity,
                "room_name": room_name,
                "stopped_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to remove agent from room {room_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "room_name": room_name
            }

    async def _cleanup_agent_after_delay(self, room_name: str, delay: int = 10):
        """Clean up agent info after a delay"""
        try:
            await asyncio.sleep(delay)
            if room_name in self.active_agents:
                del self.active_agents[room_name]
                logger.info(f"🧹 Cleaned up agent info for room: {room_name}")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up agent info: {e}")

    def get_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active agents"""
        return self.active_agents.copy()

    def get_agent_info(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific agent"""
        return self.active_agents.get(room_name)

    async def update_agent_settings(
        self, 
        room_name: str, 
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update settings for an active agent
        
        Args:
            room_name: LiveKit room name
            settings: New settings to apply
            
        Returns:
            Update result
        """
        try:
            if room_name not in self.active_agents:
                return {
                    "success": False,
                    "error": "No active agent found for this room"
                }
            
            # Update settings in memory
            agent_info = self.active_agents[room_name]
            agent_info["context"]["room_settings"].update(settings)
            agent_info["last_updated"] = datetime.utcnow()
            
            logger.info(f"✅ Updated agent settings for room: {room_name}")
            
            return {
                "success": True,
                "room_name": room_name,
                "updated_settings": settings,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update agent settings: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics about agent deployment"""
        active_count = len([a for a in self.active_agents.values() if a.get("status") == "active"])
        stopped_count = len([a for a in self.active_agents.values() if a.get("status") == "stopped"])
        
        return {
            "total_agents": len(self.active_agents),
            "active_agents": active_count,
            "stopped_agents": stopped_count,
            "rooms_with_agents": list(self.active_agents.keys()),
            "timestamp": datetime.utcnow().isoformat()
        } 