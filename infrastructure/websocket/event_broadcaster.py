"""
Real-time Event Broadcaster for WebSocket
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID
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
            self._periodic_queue_updates()
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
        Check for potential matches in the queue (simplified matching logic)
        
        Args:
            queue_items: Current items in the matching queue
        """
        try:
            # Group users by preferred topics (simplified)
            topic_groups: Dict[str, List[Dict]] = {}
            
            for item in queue_items:
                if not isinstance(item, dict) or 'preferred_topics' not in item:
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
                        
                        logger.info(f"🎯 Match created: {len(user_ids)} users, topic={topic}, room={room_id}")
                        
        except Exception as e:
            logger.error(f"❌ Error checking for matches: {e}") 