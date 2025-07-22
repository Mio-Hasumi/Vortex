"""
AI Services Module for VoiceApp

This module provides AI-powered services including:
- AI Host Service (conversation management)
- Text-to-Speech (TTS) service  
- Speech-to-Text (STT) service
- Topic extraction and hashtag generation
- Real-time subtitle generation
- WaitingRoomAgent (OpenAI Realtime API-powered waiting room agent)
- VortexAgent (OpenAI Realtime API-powered conversation host)
"""

__version__ = "2.0.0"
__author__ = "VoiceApp Team"

# Export main classes
from .openai_service import OpenAIService, get_openai_service
from .ai_host_service import AIHostService, AIHostSession
from .waiting_room_agent import WaitingRoomAgent, create_waiting_room_agent_session
from .vortex_agent import VortexAgent, create_vortex_agent_session

__all__ = [
    'OpenAIService',
    'get_openai_service', 
    'AIHostService',
    'AIHostSession',
    'WaitingRoomAgent',
    'create_waiting_room_agent_session',
    'VortexAgent', 
    'create_vortex_agent_session'
] 