"""
VoiceApp FastAPI Backend
========================

AI-driven voice social platform backend API
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.routers import auth, topics, matching, rooms, friends, recordings
from infrastructure.container import container
from infrastructure.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global settings
settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan events for startup and shutdown
    """
    # Startup
    logger.info("🚀 Starting VoiceApp Backend...")
    
    # Initialize dependency injection container
    container.initialize()
    
    # Initialize Redis connection
    redis_service = container.get_redis_service()
    logger.info(f"🔥 Redis health check: {'✅ Connected' if redis_service.health_check() else '❌ Failed'}")
    
    # Initialize LiveKit connection
    livekit_service = container.get_livekit_service()
    livekit_healthy = await livekit_service.health_check()
    logger.info(f"🎥 LiveKit health check: {'✅ Connected' if livekit_healthy else '❌ Failed'}")
    
    # Start WebSocket services
    await container.start_websocket_services()
    logger.info("🔌 WebSocket services: ✅ Started")
    
    logger.info("🎯 VoiceApp Backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down VoiceApp Backend...")
    await container.shutdown()
    logger.info("✅ VoiceApp Backend shut down successfully!")

# Create FastAPI app
app = FastAPI(
    title="VoiceApp API",
    description="AI-driven voice social platform backend API",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "VoiceApp Backend API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(matching.router, prefix="/api/matching", tags=["matching"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(friends.router, prefix="/api/friends", tags=["friends"])
app.include_router(recordings.router, prefix="/api/recordings", tags=["recordings"])

# AI-powered features
from api.routers import ai_host
app.include_router(ai_host.router, prefix="/api/ai-host", tags=["ai-host"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 