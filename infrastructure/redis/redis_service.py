"""
Redis Service for queue management and caching
"""

import json
import redis
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
import asyncio
from datetime import datetime, timedelta
import logging

from infrastructure.config import Settings

logger = logging.getLogger(__name__)

def json_serializer(obj):
    """Custom JSON serializer for UUID and datetime objects"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

class RedisService:
    """Redis service for queue management and caching"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.async_redis_client: Optional[redis.asyncio.Redis] = None
        self.is_mock = False
        
    def _build_redis_url(self) -> str:
        """Build Redis URL from configuration"""
        # Priority 1: Use REDIS_PUBLIC_URL (preferred for Railway external access)
        if hasattr(self.settings, 'REDIS_PUBLIC_URL') and self.settings.REDIS_PUBLIC_URL:
            return self.settings.REDIS_PUBLIC_URL
        
        # Priority 2: Use REDIS_URL if it's not the default localhost
        if hasattr(self.settings, 'REDIS_URL') and self.settings.REDIS_URL != 'redis://localhost:6379/0':
            return self.settings.REDIS_URL
        
        # Priority 3: Build from individual components
        host = getattr(self.settings, 'REDIS_HOST', 'localhost')
        port = getattr(self.settings, 'REDIS_PORT', 6379)
        password = getattr(self.settings, 'REDIS_PASSWORD', '')
        db = getattr(self.settings, 'REDIS_DB', 0)
        
        # Build URL
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"
        
    def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            # Build Redis URL from configuration
            redis_url = self._build_redis_url()
            logger.info(f"🔍 Connecting to Redis at: {redis_url.replace(self.settings.REDIS_PASSWORD, '***') if self.settings.REDIS_PASSWORD else redis_url}")
            
            # Synchronous client
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Asynchronous client
            self.async_redis_client = redis.asyncio.from_url(
                redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            # Create mock client for development
            self.redis_client = MockRedisClient()
            self.async_redis_client = MockAsyncRedisClient()
            self.is_mock = True
            logger.warning("⚠️ Using mock Redis client for development")
    
    def disconnect(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
        if self.async_redis_client:
            asyncio.create_task(self.async_redis_client.close())
        logger.info("Redis connection closed")
    
    def health_check(self) -> bool:
        """Check Redis health"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False
    
    # Queue Management
    def enqueue(self, queue_name: str, item: Dict[str, Any], priority: int = 0) -> bool:
        """Add item to queue with priority"""
        try:
            # Add timestamp
            item['enqueued_at'] = datetime.utcnow().isoformat()
            item['priority'] = priority
            
            # Use sorted set for priority queue
            score = priority * 1000000 + int(datetime.utcnow().timestamp())
            return self.redis_client.zadd(queue_name, {json.dumps(item, default=json_serializer): score})
        except Exception as e:
            logger.error(f"Failed to enqueue item: {e}")
            return False
    
    def dequeue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Remove and return highest priority item from queue"""
        try:
            # Get highest priority item (lowest score)
            result = self.redis_client.zpopmin(queue_name)
            if result:
                item_json, score = result[0]
                return json.loads(item_json)
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue item: {e}")
            return None
    
    def peek_queue(self, queue_name: str, count: int = 1) -> List[Dict[str, Any]]:
        """Peek at queue items without removing them"""
        try:
            results = self.redis_client.zrange(queue_name, 0, count - 1, withscores=True)
            return [json.loads(item) for item, score in results]
        except Exception as e:
            logger.error(f"Failed to peek queue: {e}")
            return []
    
    def get_queue_size(self, queue_name: str) -> int:
        """Get queue size"""
        try:
            return self.redis_client.zcard(queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0
    
    def remove_from_queue(self, queue_name: str, item: Dict[str, Any]) -> bool:
        """Remove specific item from queue"""
        try:
            return self.redis_client.zrem(queue_name, json.dumps(item, default=json_serializer))
        except Exception as e:
            logger.error(f"Failed to remove from queue: {e}")
            return False
    
    def clear_queue(self, queue_name: str) -> bool:
        """Clear entire queue"""
        try:
            return self.redis_client.delete(queue_name)
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False
    
    # Caching
    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with optional TTL"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, bool):
                value = str(value).lower()  # Convert True -> "true", False -> "false"
            
            if ttl:
                return self.redis_client.setex(key, ttl, value)
            else:
                return self.redis_client.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            value = self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete cache value"""
        try:
            return self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.redis_client.exists(key)
        except Exception as e:
            logger.error(f"Failed to check key existence: {e}")
            return False
    
    # User Session Management
    def set_user_online(self, user_id: UUID, ttl: int = 3600) -> bool:
        """Mark user as online"""
        return self.set_cache(f"user:online:{user_id}", "1", ttl)
    
    def set_user_offline(self, user_id: UUID) -> bool:
        """Mark user as offline"""
        return self.delete_cache(f"user:online:{user_id}")
    
    def is_user_online(self, user_id: UUID) -> bool:
        """Check if user is online"""
        return self.exists(f"user:online:{user_id}")
    
    def get_online_users(self) -> List[str]:
        """Get list of online users"""
        try:
            keys = self.redis_client.keys("user:online:*")
            return [key.replace("user:online:", "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []
    
    # Matching Queue Specific Methods
    def add_to_matching_queue(self, user_id: UUID, preferences: Dict[str, Any]) -> bool:
        """Add user to matching queue"""
        queue_item = {
            'user_id': str(user_id),  # Convert UUID to string
            'preferences': preferences,
            'timestamp': datetime.utcnow().isoformat()
        }
        return self.enqueue('matching_queue', queue_item, priority=0)
    
    def remove_from_matching_queue(self, user_id: UUID) -> bool:
        """Remove user from matching queue"""
        try:
            # Find and remove user from queue
            queue_items = self.redis_client.zrange('matching_queue', 0, -1, withscores=True)
            for item_json, score in queue_items:
                item = json.loads(item_json)
                if item.get('user_id') == str(user_id):
                    return self.redis_client.zrem('matching_queue', item_json)
            return False
        except Exception as e:
            logger.error(f"Failed to remove user from matching queue: {e}")
            return False
    
    def get_matching_queue_position(self, user_id: UUID) -> int:
        """Get user's position in matching queue"""
        try:
            queue_items = self.redis_client.zrange('matching_queue', 0, -1)
            for i, item_json in enumerate(queue_items):
                item = json.loads(item_json)
                if item.get('user_id') == str(user_id):
                    return i + 1
            return 0
        except Exception as e:
            logger.error(f"Failed to get queue position: {e}")
            return 0
    
    def get_matching_queue_size(self) -> int:
        """Get matching queue size"""
        return self.get_queue_size('matching_queue')
    
    def peek_matching_queue(self, count: int = 10) -> List[Dict[str, Any]]:
        """Peek at matching queue"""
        return self.peek_queue('matching_queue', count)
    
    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Get all users currently in the matching queue"""
        try:
            logger.info("🔍 Getting queue status from Redis")
            queue_items = self.redis_client.zrange('matching_queue', 0, -1, withscores=True)
            queue_data = []
            
            for item_json, score in queue_items:
                try:
                    item = json.loads(item_json)
                    queue_data.append(item)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid queue item format: {e}")
                    continue
            
            logger.info(f"✅ Retrieved {len(queue_data)} users from queue")
            return queue_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue status: {e}")
            return []
    
    def get_users_waiting_too_long(self, timeout_minutes: int = 1) -> List[Dict[str, Any]]:
        """Get users who have been waiting in queue for more than timeout_minutes"""
        try:
            queue_items = self.redis_client.zrange('matching_queue', 0, -1, withscores=True)
            timeout_users = []
            current_time = datetime.utcnow()
            
            for item_json, score in queue_items:
                try:
                    item = json.loads(item_json)
                    timestamp_str = item.get('timestamp')
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        wait_time = current_time - timestamp
                        
                        if wait_time.total_seconds() >= timeout_minutes * 60:
                            timeout_users.append({
                                'user_id': item.get('user_id'),
                                'preferences': item.get('preferences', {}),
                                'wait_time_seconds': wait_time.total_seconds(),
                                'queue_item': item_json
                            })
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Invalid queue item format: {e}")
                    continue
            
            return timeout_users
            
        except Exception as e:
            logger.error(f"Failed to get users waiting too long: {e}")
            return []
    
    def create_timeout_match(self, user1_id: str, user2_id: str) -> bool:
        """Create a timeout match between two users and remove them from queue"""
        try:
            # Remove both users from matching queue
            user1_removed = self.remove_from_matching_queue(UUID(user1_id))
            user2_removed = self.remove_from_matching_queue(UUID(user2_id))
            
            if user1_removed and user2_removed:
                # Store the timeout match info
                match_data = {
                    'user1_id': user1_id,
                    'user2_id': user2_id,
                    'match_type': 'timeout_fallback',
                    'created_at': datetime.utcnow().isoformat()
                }
                
                match_key = f"timeout_match:{user1_id}:{user2_id}"
                self.redis_client.setex(match_key, 3600, json.dumps(match_data))  # Expires in 1 hour
                
                logger.info(f"✅ Created timeout match: {user1_id} + {user2_id}")
                return True
            else:
                logger.warning(f"Failed to remove users from queue: {user1_id}, {user2_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create timeout match: {e}")
            return False


class MockRedisClient:
    """Mock Redis client for development"""
    
    def __init__(self):
        self.data = {}
        self.queues = {}
        logger.info("🔧 Mock Redis client initialized")
    
    def ping(self) -> bool:
        return True
    
    def close(self) -> None:
        pass
    
    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        if name not in self.queues:
            self.queues[name] = []
        for item, score in mapping.items():
            self.queues[name].append((item, score))
        self.queues[name].sort(key=lambda x: x[1])
        return len(mapping)
    
    def zpopmin(self, name: str, count: int = 1) -> List[tuple]:
        if name not in self.queues or not self.queues[name]:
            return []
        items = self.queues[name][:count]
        self.queues[name] = self.queues[name][count:]
        return items
    
    def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> List:
        if name not in self.queues:
            return []
        items = self.queues[name][start:end+1] if end != -1 else self.queues[name][start:]
        if withscores:
            return items
        return [item for item, score in items]
    
    def zcard(self, name: str) -> int:
        return len(self.queues.get(name, []))
    
    def zrem(self, name: str, *values) -> int:
        if name not in self.queues:
            return 0
        original_length = len(self.queues[name])
        self.queues[name] = [(item, score) for item, score in self.queues[name] if item not in values]
        return original_length - len(self.queues[name])
    
    def delete(self, *names) -> int:
        count = 0
        for name in names:
            if name in self.data:
                del self.data[name]
                count += 1
            if name in self.queues:
                del self.queues[name]
                count += 1
        return count
    
    def set(self, name: str, value: Any) -> bool:
        self.data[name] = value
        return True
    
    def setex(self, name: str, time: int, value: Any) -> bool:
        self.data[name] = value
        return True
    
    def get(self, name: str) -> Optional[Any]:
        return self.data.get(name)
    
    def exists(self, name: str) -> bool:
        return name in self.data
    
    def keys(self, pattern: str) -> List[str]:
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return [key for key in self.data.keys() if key.startswith(prefix)]
        return [key for key in self.data.keys() if key == pattern]


class MockAsyncRedisClient:
    """Mock async Redis client for development"""
    
    def __init__(self):
        self.sync_client = MockRedisClient()
        logger.info("🔧 Mock async Redis client initialized")
    
    async def close(self) -> None:
        pass
    
    async def ping(self) -> bool:
        return True 