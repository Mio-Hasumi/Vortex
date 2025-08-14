"""
WebSocket Connection Manager
"""

import json
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID
import asyncio
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from infrastructure.redis.redis_service import RedisService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager with Redis integration
    """
    
    def __init__(self, redis_service: RedisService):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        
        # Connection metadata: {connection_id: user_info}
        self.connection_metadata: Dict[str, Dict] = {}
        
        # Redis service for state management
        self.redis = redis_service
        
        # Background tasks
        self._running_tasks: Set[asyncio.Task] = set()
        
        logger.info("🔌 WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, user_id: UUID, connection_type: str = "general") -> str:
        """
        Add a new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            user_id: User's UUID
            connection_type: Type of connection (matching, general, etc.)
            
        Returns:
            Connection ID
        """
        try:
            await websocket.accept()
            
            # Generate connection ID
            connection_id = f"{user_id}_{connection_type}_{datetime.utcnow().timestamp()}"
            user_id_str = str(user_id)
            
            # Initialize user connections if first connection
            if user_id_str not in self.active_connections:
                self.active_connections[user_id_str] = {}
            
            # Store connection
            self.active_connections[user_id_str][connection_id] = websocket
            
            # Store metadata
            self.connection_metadata[connection_id] = {
                "user_id": user_id_str,
                "connection_type": connection_type,
                "connected_at": datetime.utcnow().isoformat(),
                "last_ping": datetime.utcnow().isoformat()
            }
            
            # Mark user as online in Redis
            self.redis.set_user_online(user_id, ttl=7200)  # 2 hours TTL
            
            logger.info(f"✅ WebSocket connected: user={user_id}, type={connection_type}, id={connection_id}")
            
            # Send welcome message
            await self._send_to_connection(connection_id, {
                "type": "welcome",
                "connection_id": connection_id,
                "user_id": user_id_str,
                "message": f"Successfully connected to {connection_type} WebSocket",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Start background monitoring for this connection
            task = asyncio.create_task(self._monitor_connection(connection_id))
            self._running_tasks.add(task)
            task.add_done_callback(self._running_tasks.discard)
            
            return connection_id
            
        except Exception as e:
            logger.error(f"❌ Failed to establish WebSocket connection for user {user_id}: {e}")
            raise
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection with improved cleanup
        
        Args:
            connection_id: Connection ID to remove
        """
        try:
            if connection_id not in self.connection_metadata:
                logger.debug(f"👋 Connection {connection_id} already cleaned up")
                return
            
            metadata = self.connection_metadata[connection_id]
            user_id_str = metadata["user_id"]
            connection_type = metadata.get("connection_type", "unknown")
            
            logger.debug(f"👋 Disconnecting {connection_type} connection {connection_id} for user {user_id_str}")
            
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                logger.error(f"❌ Invalid user_id format in connection metadata: {user_id_str}")
                user_id = None
            
            # Close WebSocket connection gracefully if still open
            if user_id_str in self.active_connections and connection_id in self.active_connections[user_id_str]:
                websocket = self.active_connections[user_id_str][connection_id]
                try:
                    await websocket.close(code=1000, reason="Server disconnect")
                except Exception:
                    pass  # Connection might already be closed
            
            # Remove from active connections
            if user_id_str in self.active_connections:
                self.active_connections[user_id_str].pop(connection_id, None)
                
                # If no more connections for user, mark as offline
                if not self.active_connections[user_id_str]:
                    del self.active_connections[user_id_str]
                    
                    if user_id:
                        self.redis.set_user_offline(user_id)
                        # Clean up user from matching queue if they were matching
                        self.redis.remove_from_matching_queue(user_id)
                        logger.info(f"👋 User {user_id_str} marked offline (no more connections)")
            
            # Remove metadata
            self.connection_metadata.pop(connection_id, None)
            
            logger.debug(f"👋 WebSocket cleanup completed: {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error during WebSocket disconnect for {connection_id}: {e}")
            # Force cleanup even on error
            try:
                self.connection_metadata.pop(connection_id, None)
                # Try to remove from active connections
                for user_connections in self.active_connections.values():
                    user_connections.pop(connection_id, None)
            except Exception:
                pass
    
    async def send_to_user(self, user_id: UUID, message: Dict) -> bool:
        """
        Send message to all connections of a specific user
        
        Args:
            user_id: Target user's UUID
            message: Message to send
            
        Returns:
            True if message was sent to at least one connection
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self.active_connections:
            logger.warning(f"⚠️ No active connections for user {user_id}")
            return False
        
        sent_count = 0
        connections_to_remove = []
        
        for connection_id, websocket in self.active_connections[user_id_str].items():
            try:
                await websocket.send_text(json.dumps(message))
                sent_count += 1
                
                # Update last ping
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_ping"] = datetime.utcnow().isoformat()
                    
            except WebSocketDisconnect:
                logger.info(f"📡 WebSocket disconnected during send: {connection_id}")
                connections_to_remove.append(connection_id)
            except Exception as e:
                logger.error(f"❌ Error sending to {connection_id}: {e}")
                connections_to_remove.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in connections_to_remove:
            await self.disconnect(connection_id)
        
        logger.debug(f"📤 Message sent to {sent_count} connections for user {user_id}")
        return sent_count > 0
    
    async def broadcast_to_type(self, connection_type: str, message: Dict, exclude_user_id: Optional[UUID] = None) -> int:
        """
        Broadcast message to all connections of a specific type
        
        Args:
            connection_type: Type of connections to broadcast to
            message: Message to broadcast
            exclude_user_id: Optional user ID to exclude from broadcast
            
        Returns:
            Number of connections message was sent to
        """
        sent_count = 0
        exclude_user_str = str(exclude_user_id) if exclude_user_id else None
        
        for connection_id, metadata in self.connection_metadata.items():
            if metadata["connection_type"] != connection_type:
                continue
                
            if exclude_user_str and metadata["user_id"] == exclude_user_str:
                continue
            
            if await self._send_to_connection(connection_id, message):
                sent_count += 1
        
        logger.debug(f"📡 Broadcasted to {sent_count} {connection_type} connections")
        return sent_count
    
    async def get_online_users(self) -> List[str]:
        """Get list of currently connected user IDs"""
        return list(self.active_connections.keys())
    
    async def is_user_connected(self, user_id: UUID) -> bool:
        """Check if user has any active WebSocket connections"""
        user_id_str = str(user_id)
        is_connected = user_id_str in self.active_connections and len(self.active_connections[user_id_str]) > 0
        
        logger.debug(f"🔍 [CONNECTION_CHECK] User {user_id}: connected={is_connected}")
        if user_id_str in self.active_connections:
            logger.debug(f"   📊 Connection count: {len(self.active_connections[user_id_str])}")
            logger.debug(f"   🔗 Connection IDs: {list(self.active_connections[user_id_str].keys())}")
        else:
            logger.debug(f"   ❌ User not in active_connections at all")
            
        return is_connected
    
    async def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        
        return {
            "total_connections": total_connections,
            "connected_users": len(self.active_connections),
            "connection_types": self._get_connection_type_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_connection_type_stats(self) -> Dict[str, int]:
        """Get statistics by connection type"""
        stats = {}
        for metadata in self.connection_metadata.values():
            conn_type = metadata["connection_type"]
            stats[conn_type] = stats.get(conn_type, 0) + 1
        return stats
    
    async def _send_to_connection(self, connection_id: str, message: Dict) -> bool:
        """
        Send message to a specific connection with improved error handling
        
        Args:
            connection_id: Connection ID
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        if connection_id not in self.connection_metadata:
            logger.debug(f"📤 Connection {connection_id} not found in metadata")
            return False
        
        metadata = self.connection_metadata[connection_id]
        user_id_str = metadata["user_id"]
        
        if user_id_str not in self.active_connections:
            logger.debug(f"📤 User {user_id_str} not found in active connections")
            return False
        
        if connection_id not in self.active_connections[user_id_str]:
            logger.debug(f"📤 Connection {connection_id} not found for user {user_id_str}")
            return False
        
        websocket = self.active_connections[user_id_str][connection_id]
        message_type = message.get("type", "unknown")
        
        try:
            await websocket.send_text(json.dumps(message))
            
            # Only log non-ping messages to reduce noise
            if message_type != "ping":
                logger.debug(f"📤 Sent {message_type} to {connection_id}")
            
            return True
            
        except WebSocketDisconnect:
            logger.info(f"📤 WebSocket disconnected for {connection_id} while sending {message_type}")
            # Don't call disconnect() here to avoid recursive calls
            return False
        except ConnectionResetError:
            logger.info(f"📤 Connection reset for {connection_id} while sending {message_type}")
            return False
        except Exception as e:
            # Only log non-connection errors as warnings/errors
            if "ConnectionClosed" in str(e) or "ConnectionClosedError" in str(type(e).__name__):
                logger.debug(f"📤 Connection closed for {connection_id} while sending {message_type}: {e}")
            else:
                logger.error(f"❌ Unexpected error sending {message_type} to connection {connection_id}: {e}")
            return False
    
    async def _monitor_connection(self, connection_id: str) -> None:
        """
        Monitor a WebSocket connection for health with improved heartbeat mechanism
        
        Args:
            connection_id: Connection ID to monitor
        """
        logger.debug(f"🔍 Starting connection monitoring for {connection_id}")
        ping_failures = 0
        max_ping_failures = 3
        
        try:
            # Send periodic pings to keep connection alive
            while connection_id in self.connection_metadata:
                await asyncio.sleep(45)  # Ping every 45 seconds (less aggressive)
                
                # Check if connection still exists
                if connection_id not in self.connection_metadata:
                    logger.debug(f"🔍 Connection {connection_id} no longer exists, stopping monitoring")
                    break
                
                # Send ping
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat(),
                    "sequence": ping_failures
                }
                
                logger.debug(f"📡 Sending ping to {connection_id}")
                
                if not await self._send_to_connection(connection_id, ping_message):
                    ping_failures += 1
                    logger.warning(f"📡 Ping failed for {connection_id} (attempt {ping_failures}/{max_ping_failures})")
                    
                    if ping_failures >= max_ping_failures:
                        logger.warning(f"📡 Max ping failures reached for {connection_id}, cleaning up")
                        break
                else:
                    # Reset failure count on success
                    if ping_failures > 0:
                        logger.debug(f"📡 Ping successful for {connection_id}, reset failure count")
                        ping_failures = 0
                        
        except asyncio.CancelledError:
            logger.debug(f"🔍 Connection monitoring cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"❌ Error monitoring connection {connection_id}: {e}")
        finally:
            # Only cleanup if connection is still tracked
            if connection_id in self.connection_metadata:
                logger.debug(f"🧹 Cleaning up monitored connection {connection_id}")
                await self.disconnect(connection_id)
    
    async def cleanup(self) -> None:
        """Cleanup all connections and tasks"""
        logger.info("🧹 Cleaning up WebSocket Connection Manager")
        
        # Cancel all monitoring tasks
        for task in self._running_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        # Close all connections
        for user_connections in self.active_connections.values():
            for websocket in user_connections.values():
                try:
                    await websocket.close()
                except:
                    pass
        
        # Clear data structures
        self.active_connections.clear()
        self.connection_metadata.clear()
        
        logger.info("✅ WebSocket Connection Manager cleanup complete") 
    
    async def join_room(self, room_name: str, user_id: UUID, websocket: WebSocket) -> str:
        """
        Join a user to a specific room
        
        Args:
            room_name: Name of the room to join
            user_id: User's UUID
            websocket: WebSocket connection
            
        Returns:
            Connection ID for this room connection
        """
        try:
            # Generate unique connection ID
            connection_id = f"{user_id}_room_{room_name}_{datetime.utcnow().timestamp()}"
            
            # Store connection in room-specific storage
            user_id_str = str(user_id)
            if user_id_str not in self.active_connections:
                self.active_connections[user_id_str] = {}
            
            self.active_connections[user_id_str][connection_id] = websocket
            
            # Store metadata
            self.connection_metadata[connection_id] = {
                "user_id": user_id_str,
                "connection_type": "room",
                "room_name": room_name,
                "connected_at": datetime.utcnow().isoformat()
            }
            
            # Update Redis state
            self.redis.set_user_online(user_id)
            
            logger.info(f"✅ User joined room via WebSocket: user={user_id}, room={room_name}, id={connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"❌ Failed to join room: {e}")
            raise
    
    async def leave_room(self, room_name: str, connection_id: str) -> bool:
        """
        Remove a user from a specific room
        
        Args:
            room_name: Name of the room to leave
            connection_id: Connection ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            # Find and remove the connection
            for user_id, connections in self.active_connections.items():
                if connection_id in connections:
                    # Close the WebSocket
                    websocket = connections[connection_id]
                    try:
                        await websocket.close()
                    except:
                        pass
                    
                    # Remove from connections
                    del connections[connection_id]
                    
                    # Remove metadata
                    if connection_id in self.connection_metadata:
                        del self.connection_metadata[connection_id]
                    
                    # Update Redis if no more connections
                    if not connections:
                        self.redis.set_user_offline(UUID(user_id))
                    
                    logger.info(f"✅ User left room via WebSocket: user={user_id}, room={room_name}, connection={connection_id}")
                    return True
            
            logger.warning(f"⚠️ Connection not found for removal: {connection_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to leave room: {e}")
            return False
    
    async def broadcast_to_room(self, room_name: str, message: Dict, exclude_connection_id: Optional[str] = None) -> int:
        """
        Broadcast message to all users in a specific room
        
        Args:
            room_name: Name of the room
            message: Message to broadcast
            exclude_connection_id: Optional connection to exclude
            
        Returns:
            Number of users who received the message
        """
        sent_count = 0
        
        try:
            # Find all connections for this room
            for connection_id, metadata in self.connection_metadata.items():
                if (metadata.get("connection_type") == "room" and 
                    metadata.get("room_name") == room_name and
                    connection_id != exclude_connection_id):
                    
                    success = await self._send_to_connection(connection_id, message)
                    if success:
                        sent_count += 1
            
            logger.info(f"📡 Broadcasted to room {room_name}: {sent_count} recipients")
            return sent_count
            
        except Exception as e:
            logger.error(f"❌ Failed to broadcast to room {room_name}: {e}")
            return sent_count
    
    async def get_room_participants(self, room_name: str) -> List[str]:
        """
        Get list of user IDs currently in a room
        
        Args:
            room_name: Name of the room
            
        Returns:
            List of user IDs in the room
        """
        try:
            participants = []
            for connection_id, metadata in self.connection_metadata.items():
                if (metadata.get("connection_type") == "room" and 
                    metadata.get("room_name") == room_name):
                    user_id = metadata.get("user_id")
                    if user_id and user_id not in participants:
                        participants.append(user_id)
            
            return participants
            
        except Exception as e:
            logger.error(f"❌ Failed to get room participants: {e}")
            return [] 