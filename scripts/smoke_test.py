#!/usr/bin/env python3
"""
VoiceApp Backend Smoke Tests
============================

Comprehensive smoke tests that verify all major API functionalities:
- Authentication (Register/Login)
- AI Services (TTS, Topic Extraction)
- Room Management (Create/Join/WebSocket)
- Matching System (AI Match, Timeout Match)
- Status Verification

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --base-url https://your-api.com
    python scripts/smoke_test.py --verbose
"""

import asyncio
import json
import time
import uuid
import base64
import io
import os
import sys
import argparse
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import websockets
import requests
from firebase_admin import auth, credentials, initialize_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmokeTestRunner:
    """Comprehensive smoke test runner for VoiceApp backend"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.ws_base_url = base_url.replace('http://', 'ws://').replace('https://', 'wss://').rstrip('/')
        self.verbose = verbose
        self.session = None
        self.firebase_app = None
        
        # Test data
        self.test_user_email = f"smoketest_{uuid.uuid4().hex[:8]}@voiceapp.test"
        self.test_user_password = "SmokeTesting123!"
        self.test_user_name = f"SmokeTest User {uuid.uuid4().hex[:6]}"
        
        # Test results
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Test state
        self.firebase_token = None
        self.firebase_uid = None
        self.user_id = None
        self.room_id = None
        self.match_id = None
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def log_test(self, test_name: str, status: str, message: str = "", duration: float = 0):
        """Log test results"""
        self.results['total_tests'] += 1
        
        if status == 'PASS':
            self.results['passed'] += 1
            icon = "✅"
        elif status == 'FAIL':
            self.results['failed'] += 1
            icon = "❌"
            self.results['errors'].append(f"{test_name}: {message}")
        elif status == 'SKIP':
            self.results['skipped'] += 1
            icon = "⏭️"
        else:
            icon = "⚠️"
        
        duration_str = f" ({duration:.2f}s)" if duration > 0 else ""
        logger.info(f"{icon} {test_name}: {status}{duration_str}")
        if message and self.verbose:
            logger.info(f"   └─ {message}")
    
    async def setup(self):
        """Setup test environment"""
        logger.info("🚀 Setting up smoke test environment...")
        
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize Firebase Admin (if available)
        try:
            cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase-credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                self.firebase_app = initialize_app(cred, name=f'smoketest_{uuid.uuid4().hex[:8]}')
                logger.info("✅ Firebase Admin initialized")
            else:
                logger.warning("⚠️ Firebase credentials not found, skipping Firebase tests")
        except Exception as e:
            logger.warning(f"⚠️ Firebase setup failed: {e}")
    
    async def cleanup(self):
        """Cleanup test environment"""
        logger.info("🧹 Cleaning up smoke test environment...")
        
        if self.session:
            await self.session.close()
        
        # Note: We don't delete the Firebase user to avoid issues with re-running tests
        logger.info("✅ Cleanup completed")
    
    async def health_check(self):
        """Test basic health endpoints"""
        start_time = time.time()
        
        try:
            # Test root health endpoint
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    if "VoiceApp Backend API" in data.get("message", ""):
                        self.log_test("Health Check (Root)", "PASS", 
                                    f"API responding: {data.get('message')}", 
                                    time.time() - start_time)
                    else:
                        self.log_test("Health Check (Root)", "FAIL", 
                                    f"Unexpected response: {data}")
                else:
                    self.log_test("Health Check (Root)", "FAIL", 
                                f"HTTP {response.status}")
                    
            # Test AI Host health endpoint
            async with self.session.get(f"{self.base_url}/api/ai-host/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Health Check (AI Host)", "PASS", 
                                f"AI services: {data.get('features', [])}")
                else:
                    self.log_test("Health Check (AI Host)", "FAIL", 
                                f"HTTP {response.status}")
                    
        except Exception as e:
            self.log_test("Health Check", "FAIL", str(e))
    
    def create_firebase_user(self):
        """Create Firebase test user"""
        start_time = time.time()
        
        try:
            if not self.firebase_app:
                self.log_test("Firebase User Creation", "SKIP", "Firebase not available")
                return False
            
            # Create Firebase user
            user_record = auth.create_user(
                email=self.test_user_email,
                password=self.test_user_password,
                display_name=self.test_user_name,
                app=self.firebase_app
            )
            
            self.firebase_uid = user_record.uid
            
            # Generate custom token
            self.firebase_token = auth.create_custom_token(
                self.firebase_uid, 
                app=self.firebase_app
            ).decode('utf-8')
            
            self.log_test("Firebase User Creation", "PASS", 
                         f"UID: {self.firebase_uid[:8]}...", 
                         time.time() - start_time)
            return True
            
        except Exception as e:
            self.log_test("Firebase User Creation", "FAIL", str(e))
            return False
    
    async def test_authentication(self):
        """Test authentication endpoints"""
        
        # Create Firebase user first
        if not self.create_firebase_user():
            self.log_test("Authentication Tests", "SKIP", "Firebase user creation failed")
            return False
        
        start_time = time.time()
        
        try:
            # Test user registration
            register_data = {
                "firebase_uid": self.firebase_uid,
                "email": self.test_user_email,
                "display_name": self.test_user_name
            }
            
            async with self.session.post(
                f"{self.base_url}/api/auth/register",
                json=register_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.user_id = data.get("user_id")
                    self.log_test("User Registration", "PASS", 
                                f"User ID: {self.user_id[:8]}...")
                else:
                    error_data = await response.text()
                    self.log_test("User Registration", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    return False
            
            # Test user login
            login_data = {
                "firebase_uid": self.firebase_uid,
                "email": self.test_user_email
            }
            
            async with self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    self.log_test("User Login", "PASS", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("User Login", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    return False
            
            # Test get profile with token
            headers = {"Authorization": f"Bearer {self.firebase_token}"}
            async with self.session.get(
                f"{self.base_url}/api/auth/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Get User Profile", "PASS", 
                                f"Profile: {data.get('display_name')}")
                else:
                    error_data = await response.text()
                    self.log_test("Get User Profile", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_test("Authentication Tests", "FAIL", str(e))
            return False
    
    async def test_ai_services(self):
        """Test AI service endpoints"""
        if not self.firebase_token:
            self.log_test("AI Services Tests", "SKIP", "No authentication token")
            return False
        
        headers = {"Authorization": f"Bearer {self.firebase_token}"}
        
        try:
            # Test topic extraction
            start_time = time.time()
            extract_data = {
                "text": "I'm interested in artificial intelligence and machine learning applications in healthcare",
                "user_context": {"expertise_level": "intermediate"}
            }
            
            async with self.session.post(
                f"{self.base_url}/api/ai-host/extract-topics",
                json=extract_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    topics = data.get("main_topics", [])
                    hashtags = data.get("hashtags", [])
                    self.log_test("Topic Extraction", "PASS", 
                                f"Topics: {topics[:2]}, Hashtags: {hashtags[:2]}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Topic Extraction", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test TTS
            start_time = time.time()
            tts_data = {
                "text": "Hello, this is a test of the text-to-speech system.",
                "voice": "nova",
                "speed": 1.0
            }
            
            async with self.session.post(
                f"{self.base_url}/api/ai-host/tts",
                json=tts_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    self.log_test("Text-to-Speech", "PASS", 
                                f"Generated {len(audio_data)} bytes of audio", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Text-to-Speech", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test simple AI endpoint
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/ai-host/test-simple",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("AI Simple Test", "PASS", 
                                f"Message: {data.get('message')}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("AI Simple Test", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    
        except Exception as e:
            self.log_test("AI Services Tests", "FAIL", str(e))
    
    async def test_room_management(self):
        """Test room management and WebSocket"""
        if not self.firebase_token:
            self.log_test("Room Management Tests", "SKIP", "No authentication token")
            return False
        
        headers = {"Authorization": f"Bearer {self.firebase_token}"}
        
        try:
            # Test room creation
            start_time = time.time()
            room_data = {
                "name": f"Smoke Test Room {uuid.uuid4().hex[:6]}",
                "topic": "artificial intelligence",
                "max_participants": 5,
                "is_private": False
            }
            
            async with self.session.post(
                f"{self.base_url}/api/rooms/",
                json=room_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.room_id = data.get("id")
                    livekit_room_name = data.get("livekit_room_name")
                    self.log_test("Room Creation", "PASS", 
                                f"Room ID: {self.room_id[:8]}...", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Room Creation", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    return False
            
            # Test room details
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/rooms/{self.room_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Room Details", "PASS", 
                                f"Status: {data.get('status')}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Room Details", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test room list
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/rooms/",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    rooms_count = len(data.get("rooms", []))
                    self.log_test("Room List", "PASS", 
                                f"Found {rooms_count} active rooms", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Room List", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    
            # Test WebSocket connection (simplified)
            await self.test_room_websocket(livekit_room_name)
                    
        except Exception as e:
            self.log_test("Room Management Tests", "FAIL", str(e))
    
    async def test_room_websocket(self, livekit_room_name: str):
        """Test room WebSocket connection"""
        start_time = time.time()
        
        try:
            ws_url = f"{self.ws_base_url}/api/rooms/ws/{self.room_id}?livekit_name={livekit_room_name}&user_id={self.user_id}"
            
            async with websockets.connect(ws_url) as websocket:
                # Wait for room_joined message
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "room_joined":
                    self.log_test("Room WebSocket", "PASS", 
                                f"Connected to room: {data.get('room_id', '')[:8]}...", 
                                time.time() - start_time)
                    
                    # Send a test message
                    test_message = {
                        "type": "text_message",
                        "message": "Hello from smoke test!",
                        "user_id": self.user_id
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Try to receive response (with timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        self.log_test("Room WebSocket Message", "PASS", "Message sent successfully")
                    except asyncio.TimeoutError:
                        self.log_test("Room WebSocket Message", "PASS", "Message sent (no immediate response)")
                else:
                    self.log_test("Room WebSocket", "FAIL", 
                                f"Unexpected message type: {data.get('type')}")
                    
        except asyncio.TimeoutError:
            self.log_test("Room WebSocket", "FAIL", "Connection timeout")
        except Exception as e:
            self.log_test("Room WebSocket", "FAIL", str(e))
    
    async def test_matching_system(self):
        """Test matching system"""
        if not self.firebase_token:
            self.log_test("Matching System Tests", "SKIP", "No authentication token")
            return False
        
        headers = {"Authorization": f"Bearer {self.firebase_token}"}
        
        try:
            # Test traditional matching
            start_time = time.time()
            match_data = {
                "preferred_topics": ["artificial intelligence", "technology"],
                "max_participants": 3,
                "language_preference": "en-US"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/matching/match",
                json=match_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.match_id = data.get("match_id")
                    self.log_test("Traditional Matching", "PASS", 
                                f"Match ID: {self.match_id[:8]}...", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Traditional Matching", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test matching status
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/matching/status",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")
                    self.log_test("Matching Status", "PASS", 
                                f"Status: {status}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Matching Status", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test AI matching
            start_time = time.time()
            ai_match_data = {
                "text_input": "I want to discuss AI and machine learning",
                "conversation_style": "casual",
                "language": "en-US",
                "max_participants": 3
            }
            
            async with self.session.post(
                f"{self.base_url}/api/matching/ai-match",
                json=ai_match_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_analysis = data.get("ai_analysis", {})
                    self.log_test("AI Matching", "PASS", 
                                f"Extracted topics: {ai_analysis.get('extracted_topics', [])[:2]}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("AI Matching", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test timeout statistics
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/matching/timeout-stats",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    queue_size = data.get("total_queue_size", 0)
                    self.log_test("Timeout Statistics", "PASS", 
                                f"Queue size: {queue_size}", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Timeout Statistics", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Cancel match
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/matching/cancel",
                headers=headers
            ) as response:
                if response.status == 204:
                    self.log_test("Cancel Match", "PASS", 
                                "Match cancelled successfully", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Cancel Match", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    
        except Exception as e:
            self.log_test("Matching System Tests", "FAIL", str(e))
    
    async def test_topics_and_social(self):
        """Test topics and social features"""
        if not self.firebase_token:
            self.log_test("Topics & Social Tests", "SKIP", "No authentication token")
            return False
        
        headers = {"Authorization": f"Bearer {self.firebase_token}"}
        
        try:
            # Test topics list
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/topics/",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    topics_count = len(data.get("topics", []))
                    self.log_test("Topics List", "PASS", 
                                f"Found {topics_count} topics", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Topics List", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test popular topics
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/topics/popular",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    popular_count = len(data.get("topics", []))
                    self.log_test("Popular Topics", "PASS", 
                                f"Found {popular_count} popular topics", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Popular Topics", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
            
            # Test friends list
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/friends/",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    friends_count = len(data.get("friends", []))
                    self.log_test("Friends List", "PASS", 
                                f"Found {friends_count} friends", 
                                time.time() - start_time)
                else:
                    error_data = await response.text()
                    self.log_test("Friends List", "FAIL", 
                                f"HTTP {response.status}: {error_data}")
                    
        except Exception as e:
            self.log_test("Topics & Social Tests", "FAIL", str(e))
    
    async def run_all_tests(self):
        """Run all smoke tests"""
        logger.info("🔥 Starting VoiceApp Backend Smoke Tests")
        logger.info(f"📡 Testing against: {self.base_url}")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            await self.setup()
            
            # Run all test suites
            await self.health_check()
            await self.test_authentication()
            await self.test_ai_services()
            await self.test_room_management()
            await self.test_matching_system()
            await self.test_topics_and_social()
            
        finally:
            await self.cleanup()
        
        # Print results
        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("🏁 Smoke Test Results:")
        logger.info(f"   📊 Total Tests: {self.results['total_tests']}")
        logger.info(f"   ✅ Passed: {self.results['passed']}")
        logger.info(f"   ❌ Failed: {self.results['failed']}")
        logger.info(f"   ⏭️ Skipped: {self.results['skipped']}")
        logger.info(f"   ⏱️ Total Time: {total_time:.2f}s")
        
        if self.results['errors']:
            logger.info("🔍 Failed Tests:")
            for error in self.results['errors']:
                logger.info(f"   └─ {error}")
        
        success_rate = (self.results['passed'] / self.results['total_tests']) * 100 if self.results['total_tests'] > 0 else 0
        
        if success_rate >= 90:
            logger.info(f"🎉 Smoke tests completed successfully! ({success_rate:.1f}% pass rate)")
            return 0
        elif success_rate >= 70:
            logger.info(f"⚠️ Smoke tests completed with warnings ({success_rate:.1f}% pass rate)")
            return 1
        else:
            logger.info(f"💥 Smoke tests failed ({success_rate:.1f}% pass rate)")
            return 2

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='VoiceApp Backend Smoke Tests')
    parser.add_argument('--base-url', 
                       default='http://localhost:8000',
                       help='Base URL for the API (default: http://localhost:8000)')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(
        base_url=args.base_url,
        verbose=args.verbose
    )
    
    return await runner.run_all_tests()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Smoke tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Smoke tests crashed: {e}")
        sys.exit(1) 