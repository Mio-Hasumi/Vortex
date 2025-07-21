"""
Real-time Event Broadcaster for WebSocket
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime

from infrastructure.redis.redis_service import RedisService
from infrastructure.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """
    Monitors Redis state changes and broadcasts events to WebSocket clients
    """
    
    def __init__(self, connection_manager: ConnectionManager, redis_service: RedisService):
        self.connection_manager = connection_manager
        self.redis = redis_service
        
        # Background monitoring tasks
        self._monitoring_tasks: List[asyncio.Task] = []
        self._is_running = False
        
        logger.info("📡 Event Broadcaster initialized")
    
    async def start(self) -> None:
        """Start the event broadcaster"""
        if self._is_running:
            logger.warning("⚠️ Event Broadcaster already running")
            return
        
        self._is_running = True
        logger.info("🚀 Starting Event Broadcaster")
        
        # Start monitoring tasks
        tasks = [
            self._monitor_matching_queue(),
            self._monitor_user_status_changes(),
            self._periodic_queue_updates(),
            self._process_timeout_matches()
        ]
        
        for task_func in tasks:
            task = asyncio.create_task(task_func)
            self._monitoring_tasks.append(task)
        
        logger.info("✅ Event Broadcaster started")
    
    async def stop(self) -> None:
        """Stop the event broadcaster"""
        if not self._is_running:
            return
        
        self._is_running = False
        logger.info("🛑 Stopping Event Broadcaster")
        
        # Cancel all monitoring tasks
        for task in self._monitoring_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        logger.info("✅ Event Broadcaster stopped")
    
    async def broadcast_match_found(self, user_ids: List[UUID], room_id: UUID, topic: str) -> None:
        """
        Broadcast match found notification to specified users
        
        Args:
            user_ids: List of matched user IDs
            room_id: Created room ID
            topic: Matched topic name
        """
        message = {
            "type": "match_found",
            "room_id": str(room_id),
            "topic": topic,
            "participants": [str(uid) for uid in user_ids],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to each matched user
        for user_id in user_ids:
            await self.connection_manager.send_to_user(user_id, message)
        
        logger.info(f"📢 Match found broadcast sent to {len(user_ids)} users")
    
    async def broadcast_queue_update(self, user_id: UUID, position: int, estimated_wait_time: int) -> None:
        """
        Broadcast queue position update to a user
        
        Args:
            user_id: User's ID
            position: Current position in queue
            estimated_wait_time: Estimated wait time in seconds
        """
        message = {
            "type": "queue_update",
            "position": position,
            "estimated_wait_time": estimated_wait_time,
            "queue_size": self.redis.get_matching_queue_size(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(user_id, message)
        logger.debug(f"📊 Queue update sent to user {user_id}: position={position}")
    
    async def broadcast_user_status_change(self, user_id: UUID, is_online: bool) -> None:
        """
        Broadcast user online/offline status change to their friends
        
        Args:
            user_id: User whose status changed
            is_online: Whether user is now online
        """
        # This would need to get user's friends list and notify them
        # For now, we'll broadcast to all connected users (simplified)
        message = {
            "type": "user_status_change",
            "user_id": str(user_id),
            "is_online": is_online,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all general connections except the user themselves
        await self.connection_manager.broadcast_to_type("general", message, exclude_user_id=user_id)
        
        logger.debug(f"👤 User status change broadcast: {user_id} -> {'online' if is_online else 'offline'}")
    
    async def broadcast_friend_request(self, from_user_id: UUID, to_user_id: UUID, request_id: UUID) -> None:
        """
        Broadcast friend request notification
        
        Args:
            from_user_id: User who sent the request
            to_user_id: User who received the request
            request_id: Friend request ID
        """
        message = {
            "type": "friend_request_received",
            "from_user_id": str(from_user_id),
            "request_id": str(request_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(to_user_id, message)
        logger.info(f"👥 Friend request notification sent: {from_user_id} -> {to_user_id}")
    
    async def broadcast_ai_match_found(self, user1_id: str, user2_id: str, match_data: Dict[str, Any]) -> None:
        """
        Broadcast AI match found notification to matched users
        
        Args:
            user1_id: First user ID (string)
            user2_id: Second user ID (string)
            match_data: Match information including room details, tokens, etc.
        """
        try:
            logger.info(f"🎯🎯🎯 [BROADCAST] ===== BROADCASTING AI MATCH =====")
            logger.info(f"🎯 [BROADCAST] User 1: {user1_id}")
            logger.info(f"🎯 [BROADCAST] User 2: {user2_id}")
            logger.info(f"🎯 [BROADCAST] Match data keys: {list(match_data.keys())}")
            
            # Convert string IDs to UUIDs
            user1_uuid = UUID(user1_id)
            user2_uuid = UUID(user2_id)
            
            logger.info(f"✅ [BROADCAST] UUIDs created successfully")
            logger.info(f"   🔍 User1 UUID: {user1_uuid}")
            logger.info(f"   🔍 User2 UUID: {user2_uuid}")
            
            # Give WebSocket connections a moment to be fully established
            await asyncio.sleep(0.1)
            
            # Check if users have active WebSocket connections
            user1_connected = await self.connection_manager.is_user_connected(user1_uuid)
            user2_connected = await self.connection_manager.is_user_connected(user2_uuid)
            
            logger.info(f"🔌 [BROADCAST] Connection status:")
            logger.info(f"   👤 User1 connected: {user1_connected}")
            logger.info(f"   👤 User2 connected: {user2_connected}")
            
            if not user1_connected:
                logger.warning(f"⚠️ [BROADCAST] User1 ({user1_id}) has NO active connections!")
            if not user2_connected:
                logger.warning(f"⚠️ [BROADCAST] User2 ({user2_id}) has NO active connections!")
            
            # Get user-specific data from match_data
            user1_data = match_data["users"][user1_id]
            user2_data = match_data["users"][user2_id]
            
            logger.info(f"📊 [BROADCAST] User data extracted:")
            logger.info(f"   👤 User1 data keys: {list(user1_data.keys())}")
            logger.info(f"   👤 User2 data keys: {list(user2_data.keys())}")
            
            # Ensure hashtags are strings to prevent UUID object errors
            hashtags_str = []
            for tag in match_data["hashtags"]:
                # Convert everything to string, including UUID objects
                hashtags_str.append(str(tag))
            
            logger.info(f"🏷️ [BROADCAST] Processed hashtags: {hashtags_str}")
            
            # Process topics by removing # prefix from hashtag strings
            topics_list = []
            for tag in hashtags_str:
                # Ensure we're working with a string and remove # prefix
                tag_str = str(tag)
                if tag_str.startswith('#'):
                    topics_list.append(tag_str[1:])  # Remove # prefix
                else:
                    topics_list.append(tag_str)
            
            logger.info(f"📝 [BROADCAST] Processed topics: {topics_list}")
            
            # Create message for User 1
            message_user1 = {
                "type": "match_found",
                "match_id": match_data["match_id"],
                "session_id": match_data["session_id"],
                "room_id": match_data["room_id"],
                "livekit_token": user1_data["livekit_token"],
                "participants": user1_data["participants"],
                "topics": topics_list,
                "hashtags": hashtags_str,
                "confidence": match_data["confidence"],
                "ai_hosted": True,
                "timestamp": match_data["created_at"]
            }
            
            # Create message for User 2
            message_user2 = {
                "type": "match_found",
                "match_id": match_data["match_id"],
                "session_id": match_data["session_id"],
                "room_id": match_data["room_id"],
                "livekit_token": user2_data["livekit_token"],
                "participants": user2_data["participants"],
                "topics": topics_list,
                "hashtags": hashtags_str,
                "confidence": match_data["confidence"],
                "ai_hosted": True,
                "timestamp": match_data["created_at"]
            }
            
            logger.info(f"📦 [BROADCAST] Messages created:")
            logger.info(f"   📦 User1 message keys: {list(message_user1.keys())}")
            logger.info(f"   📦 User2 message keys: {list(message_user2.keys())}")
            logger.info(f"   🆔 Match ID: {message_user1['match_id']}")
            logger.info(f"   🏠 Room ID: {message_user1['room_id']}")
            logger.info(f"   👥 User1 participants: {len(message_user1['participants'])}")
            logger.info(f"   👥 User2 participants: {len(message_user2['participants'])}")
            
            # Send to both users with retry mechanism
            logger.info(f"📤📤📤 [BROADCAST] Sending messages to users with retry...")
            
            # Try sending to both users multiple times to ensure delivery
            max_retries = 3
            retry_delay = 0.5  # 500ms between retries
            
            user1_sent = False
            user2_sent = False
            
            for attempt in range(max_retries):
                if not user1_sent:
                    user1_sent = await self.connection_manager.send_to_user(user1_uuid, message_user1)
                    logger.info(f"📤 [BROADCAST] User1 message attempt {attempt + 1}: {user1_sent}")
                
                if not user2_sent:
                    user2_sent = await self.connection_manager.send_to_user(user2_uuid, message_user2)
                    logger.info(f"📤 [BROADCAST] User2 message attempt {attempt + 1}: {user2_sent}")
                
                # If both users received the message, we're done
                if user1_sent and user2_sent:
                    logger.info(f"✅✅✅ [BROADCAST] BOTH users received notification on attempt {attempt + 1}!")
                    break
                
                # Wait before retry
                if attempt < max_retries - 1:  # Don't wait after the last attempt
                    logger.info(f"⏳ [BROADCAST] Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
            
            # Final status check
            if user1_sent and user2_sent:
                logger.info(f"✅✅✅ [BROADCAST] AI match found notifications sent to BOTH users successfully!")
            elif user1_sent or user2_sent:
                logger.warning(f"⚠️⚠️⚠️ [BROADCAST] Only ONE user received the notification after {max_retries} attempts!")
                logger.warning(f"   User1 received: {user1_sent}")
                logger.warning(f"   User2 received: {user2_sent}")
            else:
                logger.error(f"❌❌❌ [BROADCAST] NO users received the notification after {max_retries} attempts!")
                logger.error(f"   This indicates both users have disconnected WebSockets!")
            
            logger.info(f"📊 [BROADCAST] Match details:")
            logger.info(f"   📊 Match confidence: {match_data['confidence']:.2f}")
            logger.info(f"   🏷️ Hashtags: {match_data['hashtags']}")
            logger.info(f"🎯🎯🎯 [BROADCAST] ===== BROADCAST COMPLETED =====")
            
        except Exception as e:
            logger.error(f"❌❌❌ [BROADCAST] Failed to broadcast AI match found: {e}")
            logger.exception("Full exception details:")
            logger.error(f"❌ [BROADCAST] user1_id: {user1_id}")
            logger.error(f"❌ [BROADCAST] user2_id: {user2_id}")
            logger.error(f"❌ [BROADCAST] match_data keys: {list(match_data.keys()) if match_data else 'None'}")
    
    async def _monitor_matching_queue(self) -> None:
        """Monitor matching queue for changes"""
        try:
            logger.info("🔍 Starting matching queue monitoring")
            
            while self._is_running:
                try:
                    # Get current queue
                    queue_items = self.redis.peek_matching_queue(count=50)
                    
                    # Send position updates to users in queue
                    for position, item in enumerate(queue_items, 1):
                        if isinstance(item, dict) and 'user_id' in item:
                            user_id = UUID(item['user_id'])
                            estimated_wait = position * 30  # 30 seconds per position
                            
                            await self.broadcast_queue_update(user_id, position, estimated_wait)
                    
                    # Check for potential matches (simplified logic)
                    await self._check_for_matches(queue_items)
                    
                    # Wait before next check
                    await asyncio.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    logger.error(f"❌ Error in matching queue monitoring: {e}")
                    await asyncio.sleep(30)  # Wait longer on error
                    
        except asyncio.CancelledError:
            logger.info("🔍 Matching queue monitoring cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in matching queue monitoring: {e}")
    
    async def _monitor_user_status_changes(self) -> None:
        """Monitor user online/offline status changes"""
        try:
            logger.info("👥 Starting user status monitoring")
            
            last_online_users = set()
            
            while self._is_running:
                try:
                    # Get currently online users from Redis
                    current_online_users = set(self.redis.get_online_users())
                    
                    # Detect users who went online
                    newly_online = current_online_users - last_online_users
                    for user_id_str in newly_online:
                        try:
                            user_id = UUID(user_id_str)
                            await self.broadcast_user_status_change(user_id, is_online=True)
                        except ValueError:
                            continue
                    
                    # Detect users who went offline
                    newly_offline = last_online_users - current_online_users
                    for user_id_str in newly_offline:
                        try:
                            user_id = UUID(user_id_str)
                            await self.broadcast_user_status_change(user_id, is_online=False)
                        except ValueError:
                            continue
                    
                    # Update tracking
                    last_online_users = current_online_users
                    
                    # Wait before next check
                    await asyncio.sleep(15)  # Check every 15 seconds
                    
                except Exception as e:
                    logger.error(f"❌ Error in user status monitoring: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("👥 User status monitoring cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in user status monitoring: {e}")
    
    async def _periodic_queue_updates(self) -> None:
        """Send periodic queue updates to all matching connections"""
        try:
            logger.info("⏰ Starting periodic queue updates")
            
            while self._is_running:
                try:
                    # Get queue statistics
                    queue_size = self.redis.get_matching_queue_size()
                    
                    if queue_size > 0:
                        # Send queue statistics to all matching connections
                        stats_message = {
                            "type": "queue_stats",
                            "total_users_in_queue": queue_size,
                            "average_wait_time": queue_size * 30,  # Estimated
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        await self.connection_manager.broadcast_to_type("matching", stats_message)
                    
                    # Wait before next update
                    await asyncio.sleep(60)  # Send stats every minute
                    
                except Exception as e:
                    logger.error(f"❌ Error in periodic queue updates: {e}")
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            logger.info("⏰ Periodic queue updates cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in periodic queue updates: {e}")
    
    async def _check_for_matches(self, queue_items: List[Dict]) -> None:
        """
        Check for potential matches in the queue (enhanced with AI hashtag matching)
        
        Args:
            queue_items: Current items in the matching queue
        """
        try:
            # Separate AI-driven matches from traditional topic matches
            ai_driven_users = []
            topic_based_users = []
            
            for item in queue_items:
                if not isinstance(item, dict):
                    continue
                    
                match_type = item.get('match_type', 'traditional')
                if match_type == 'ai_driven':
                    ai_driven_users.append(item)
                else:
                    topic_based_users.append(item)
            
            # Process AI-driven hashtag matching (NEW)
            await self._process_ai_hashtag_matching(ai_driven_users)
            
            # Process traditional topic matching (EXISTING)
            await self._process_traditional_topic_matching(topic_based_users)
                        
        except Exception as e:
            logger.error(f"❌ Error checking for matches: {e}")

    async def _process_ai_hashtag_matching(self, ai_users: List[Dict]) -> None:
        """
        Process AI-driven hashtag matching
        """
        try:
            if len(ai_users) < 2:
                return
                
            # Group users by hashtag similarity
            matched_pairs = []
            processed_users = set()
            
            for i, user1 in enumerate(ai_users):
                if user1.get('user_id') in processed_users:
                    continue
                    
                user1_hashtags = set(user1.get('hashtags', []))
                if not user1_hashtags:
                    continue
                    
                best_match = None
                best_similarity = 0.0
                
                # Find best matching user
                for j, user2 in enumerate(ai_users[i+1:], i+1):
                    if user2.get('user_id') in processed_users:
                        continue
                        
                    user2_hashtags = set(user2.get('hashtags', []))
                    if not user2_hashtags:
                        continue
                    
                    # Calculate hashtag similarity
                    intersection = user1_hashtags.intersection(user2_hashtags)
                    union = user1_hashtags.union(user2_hashtags)
                    similarity = len(intersection) / len(union) if union else 0
                    
                    # Require at least 20% similarity for a match
                    if similarity >= 0.2 and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = user2
                
                # Create match if good similarity found
                if best_match and best_similarity >= 0.2:
                    await self._create_ai_match(user1, best_match, best_similarity)
                    processed_users.add(user1.get('user_id'))
                    processed_users.add(best_match.get('user_id'))
                    
        except Exception as e:
            logger.error(f"❌ Error in AI hashtag matching: {e}")

    async def _process_traditional_topic_matching(self, topic_users: List[Dict]) -> None:
        """
        Process traditional topic-based matching (existing logic)
        """
        try:
            # Group users by preferred topics (simplified)
            topic_groups: Dict[str, List[Dict]] = {}
            
            for item in topic_users:
                if 'preferred_topics' not in item:
                    continue
                
                preferred_topics = item.get('preferred_topics', [])
                if not preferred_topics:
                    continue
                
                # Use first preferred topic for grouping (simplified)
                topic = preferred_topics[0] if preferred_topics else 'general'
                
                if topic not in topic_groups:
                    topic_groups[topic] = []
                
                topic_groups[topic].append(item)
            
            # Check for matches in each topic group
            for topic, users in topic_groups.items():
                if len(users) >= 2:  # Minimum 2 users for a match
                    # Create a match (simplified - take first 2 users)
                    matched_users = users[:2]
                    user_ids = []
                    
                    for user_item in matched_users:
                        try:
                            user_id = UUID(user_item['user_id'])
                            user_ids.append(user_id)
                            
                            # Remove user from matching queue
                            self.redis.remove_from_matching_queue(user_id)
                            
                        except (ValueError, KeyError):
                            continue
                    
                    if len(user_ids) >= 2:
                        # Generate a room ID (this would normally create an actual room)
                        room_id = UUID(f"00000000-0000-0000-0000-{datetime.utcnow().strftime('%Y%m%d%H%M')}")
                        
                        # Broadcast match found
                        await self.broadcast_match_found(user_ids, room_id, topic)
                        
                        logger.info(f"🎯 Traditional match created: {len(user_ids)} users, topic={topic}, room={room_id}")
                        
        except Exception as e:
            logger.error(f"❌ Error in traditional topic matching: {e}")

    async def _create_ai_match(self, user1: Dict, user2: Dict, similarity: float) -> None:
        """
        Create an AI-hosted match between two users
        """
        try:
            user1_id = UUID(user1['user_id'])
            user2_id = UUID(user2['user_id'])
            
            # Remove users from queue
            self.redis.remove_from_matching_queue(user1_id)
            self.redis.remove_from_matching_queue(user2_id)
            
            # Generate room ID for AI-hosted conversation
            room_id = UUID(f"ai-room-{uuid4().hex[:8]}")
            
            # Get common hashtags for room topic - ensure all hashtags are strings
            user1_hashtags = set(str(tag) for tag in user1.get('hashtags', []))
            user2_hashtags = set(str(tag) for tag in user2.get('hashtags', []))
            common_hashtags = list(user1_hashtags.intersection(user2_hashtags))
            
            # Create AI-friendly topic string
            if common_hashtags:
                ai_topic = f"AI guided conversation: {', '.join(common_hashtags[:3])}"
            else:
                ai_topic = "AI guided general conversation"
            
            # Broadcast AI match found with special formatting
            await self.connection_manager.broadcast_to_user(user1_id, {
                "type": "ai_match_found",
                "room_id": str(room_id),
                "partner_id": str(user2_id),
                "topic": ai_topic,
                "hashtags": common_hashtags,
                "similarity_score": similarity,
                "ai_hosted": True,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await self.connection_manager.broadcast_to_user(user2_id, {
                "type": "ai_match_found", 
                "room_id": str(room_id),
                "partner_id": str(user1_id),
                "topic": ai_topic,
                "hashtags": common_hashtags,
                "similarity_score": similarity,
                "ai_hosted": True,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"🤖 AI match created: {user1_id} + {user2_id}, similarity={similarity:.2f}, room={room_id}")
            logger.info(f"🏷️ Common hashtags: {common_hashtags}")
            
        except Exception as e:
            logger.error(f"❌ Error creating AI match: {e}")
    
    async def _process_timeout_matches(self) -> None:
        """Process users who have been waiting too long and randomly match them"""
        try:
            logger.info("🕐 Starting timeout matching monitor")
            
            while self._is_running:
                try:
                    # Import here to avoid circular imports
                    from infrastructure.container import container
                    matching_repo = container.get_matching_repository()
                    
                    # Check for users waiting over 1 minute
                    timeout_users_count = matching_repo.get_timeout_users_count(timeout_minutes=1)
                    
                    if timeout_users_count >= 2:
                        logger.info(f"🕐 Found {timeout_users_count} users waiting over 1 minute, processing matches...")
                        
                        # Process timeout matches
                        matches_created = await matching_repo.process_timeout_matches(timeout_minutes=1)
                        
                        if matches_created:
                            logger.info(f"✅ Created {len(matches_created)} timeout matches")
                            
                            # Notify matched users via WebSocket
                            for match_info in matches_created:
                                await self._notify_timeout_match(match_info)
                        else:
                            logger.info("ℹ️ No timeout matches created this round")
                    
                    # Check every 30 seconds
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Error in timeout matching: {e}")
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("🕐 Timeout matching monitor cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in timeout matching monitor: {e}")
    
    async def _notify_timeout_match(self, match_info: dict) -> None:
        """Notify users about their timeout match"""
        try:
            user1_id = UUID(match_info['user1_id'])
            user2_id = UUID(match_info['user2_id'])
            
            # Get full match data
            match_data = match_info.get('match_data', {})
            
            if match_data and 'users' in match_data:
                # Use the full AI match notification format
                await self.broadcast_ai_match_found(
                    user1_id=match_info['user1_id'],
                    user2_id=match_info['user2_id'],
                    match_data=match_data
                )
                logger.info(f"📢 Timeout match notifications sent to {user1_id} and {user2_id} using AI match format")
            else:
                # Fallback to simple timeout notification (should not happen with new code)
                message = {
                    "type": "timeout_match_found",
                    "match_id": match_info['match_id'],
                    "session_id": match_info.get('session_id', ''),
                    "room_id": match_info.get('room_id', ''),
                    "livekit_token": "",  # Would need to be generated
                    "match_type": "timeout_fallback",
                    "partner_id": str(user2_id),
                    "message": "We found you a conversation partner! You've been matched with someone who was also waiting.",
                    "wait_time": f"{match_info['wait_time_user1']:.0f} seconds",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Send to user1
                await self.connection_manager.send_to_user(user1_id, message)
                
                # Send to user2 (with swapped partner_id)
                message_user2 = message.copy()
                message_user2['partner_id'] = str(user1_id)
                message_user2['wait_time'] = f"{match_info['wait_time_user2']:.0f} seconds"
                
                await self.connection_manager.send_to_user(user2_id, message_user2)
                
                logger.info(f"📢 Timeout match notifications sent to {user1_id} and {user2_id} using fallback format")
            
        except Exception as e:
            logger.error(f"❌ Error notifying timeout match: {e}")