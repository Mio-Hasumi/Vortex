"""
Configuration settings for the VoiceApp backend
"""

import os
import json
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings
    """
    
    # Basic App Settings
    APP_NAME: str = "VoiceApp Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Railway specific
    PORT: int = 8000
    
    # API Settings
    API_V1_STR: str = "/api"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database - Firebase
    FIREBASE_PROJECT_ID: str = "voiceapp-8f09a"
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    
    # Firebase credentials from environment (for Railway)
    FIREBASE_CREDENTIALS: str = ""
    FIREBASE_CREDENTIALS_BASE64: str = ""
    
    # Legacy Firebase fields (for backward compatibility)
    GOOGLE_CLOUD_PROJECT: str = ""
    FIREBASE_PRIVATE_KEY_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_CLIENT_ID: str = ""
    FIREBASE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    FIREBASE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    FIREBASE_CLIENT_X509_CERT_URL: str = ""
    
    # Redis - Railway auto-injection support
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PUBLIC_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Railway-specific Redis variables
    REDISHOST: str = ""
    REDISPORT: int = 0
    REDISPASSWORD: str = ""
    REDISUSER: str = ""
    
    # LiveKit
    LIVEKIT_API_KEY: str = "APIQgCgiwHnYkue"
    LIVEKIT_API_SECRET: str = "Reqvp9rjEeLAe9XZOsdjGwPFs4qJcp5VEKTVIUpn40hA"
    LIVEKIT_SERVER_URL: str = "wss://voodooo-5oh49lvx.livekit.cloud"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Handle Railway Redis configuration
        # Priority 1: Use Railway-specific individual variables
        if self.REDISHOST:
            self.REDIS_HOST = self.REDISHOST
        if self.REDISPORT and self.REDISPORT > 0:
            self.REDIS_PORT = self.REDISPORT
        if self.REDISPASSWORD:
            self.REDIS_PASSWORD = self.REDISPASSWORD
        
        # Priority 2: Parse REDIS_PUBLIC_URL (preferred for external access)
        if self.REDIS_PUBLIC_URL:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.REDIS_PUBLIC_URL)
                if parsed.hostname and not self.REDISHOST:
                    self.REDIS_HOST = parsed.hostname
                if parsed.port and not self.REDISPORT:
                    self.REDIS_PORT = parsed.port
                if parsed.password and not self.REDISPASSWORD:
                    self.REDIS_PASSWORD = parsed.password
            except Exception:
                pass
        
        # Priority 3: Parse REDIS_URL if it's not localhost
        elif self.REDIS_URL and self.REDIS_URL != "redis://localhost:6379/0":
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.REDIS_URL)
                if parsed.hostname and not self.REDISHOST:
                    self.REDIS_HOST = parsed.hostname
                if parsed.port and not self.REDISPORT:
                    self.REDIS_PORT = parsed.port
                if parsed.password and not self.REDISPASSWORD:
                    self.REDIS_PASSWORD = parsed.password
            except Exception:
                pass
        
        # Handle Railway Firebase credentials injection
        if self.FIREBASE_CREDENTIALS:
            try:
                # Write credentials to file if provided as environment variable
                credentials_path = "/tmp/firebase-credentials.json"
                with open(credentials_path, "w") as f:
                    if self.FIREBASE_CREDENTIALS.startswith("{"):
                        # Already JSON string
                        f.write(self.FIREBASE_CREDENTIALS)
                    else:
                        # Base64 encoded or other format
                        import base64
                        decoded = base64.b64decode(self.FIREBASE_CREDENTIALS)
                        f.write(decoded.decode('utf-8'))
                
                self.FIREBASE_CREDENTIALS_PATH = credentials_path
                
                # Also parse for project ID
                cred_data = json.loads(self.FIREBASE_CREDENTIALS if self.FIREBASE_CREDENTIALS.startswith("{") else base64.b64decode(self.FIREBASE_CREDENTIALS).decode('utf-8'))
                if "project_id" in cred_data:
                    self.FIREBASE_PROJECT_ID = cred_data["project_id"]
                    
            except Exception as e:
                print(f"Warning: Could not process Firebase credentials: {e}")
                
        # Handle Railway port injection
        railway_port = os.environ.get("PORT")
        if railway_port:
            self.PORT = int(railway_port)


# Global settings instance
settings = Settings() 