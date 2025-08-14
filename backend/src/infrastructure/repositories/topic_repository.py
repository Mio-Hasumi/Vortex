"""
Topic Repository implementation using Firebase
"""

import logging
from typing import Optional, List
from uuid import UUID

from domain.entities import Topic, new_topic
from infrastructure.db.firebase import FirebaseAdminService

logger = logging.getLogger(__name__)


class TopicRepository:
    """
    Topic repository implementation using Firebase Firestore
    """
    
    def __init__(self, firebase_service: FirebaseAdminService):
        self.firebase = firebase_service
        self.collection_name = "topics"
    
    def save(self, topic: Topic) -> Topic:
        """
        Save topic to Firebase Firestore
        
        Args:
            topic: Topic entity to save
            
        Returns:
            Saved topic entity
        """
        try:
            topic_data = self._entity_to_dict(topic)
            
            # Save to Firestore
            self.firebase.add_document(
                self.collection_name,
                topic_data,
                str(topic.id)
            )
            
            logger.info(f"✅ Topic saved successfully: {topic.id}")
            return topic
            
        except Exception as e:
            logger.error(f"❌ Failed to save topic {topic.id}: {e}")
            raise
    
    def find_by_id(self, topic_id: UUID) -> Optional[Topic]:
        """
        Find topic by ID
        
        Args:
            topic_id: Topic's UUID
            
        Returns:
            Topic entity or None if not found
        """
        try:
            topic_data = self.firebase.get_document(
                self.collection_name,
                str(topic_id)
            )
            
            if topic_data:
                return self._dict_to_entity(topic_data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to find topic {topic_id}: {e}")
            return None
    
    def find_all_active(self, limit: int = 50, offset: int = 0) -> List[Topic]:
        """
        Find all active topics
        
        Args:
            limit: Maximum number of topics to return
            offset: Number of topics to skip
            
        Returns:
            List of active topic entities
        """
        try:
            topics_data = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "is_active", "operator": "==", "value": True}],
                limit=limit
                # Removed order_by to avoid composite index requirement
            )
            
            # Sort by name in application layer
            topics = [self._dict_to_entity(topic_data) for topic_data in topics_data]
            topics.sort(key=lambda x: x.name)
            
            return topics
            
        except Exception as e:
            logger.error(f"❌ Failed to find active topics: {e}")
            return []
    
    def get_all_topics(self, limit: int = 50, offset: int = 0) -> List[Topic]:
        """
        Get all topics (active and inactive)
        
        Args:
            limit: Maximum number of topics to return
            offset: Number of topics to skip
            
        Returns:
            List of all topic entities
        """
        try:
            topics_data = self.firebase.query_documents(
                self.collection_name,
                filters=[],  # No filters - get all topics
                limit=limit,
                order_by="name"
            )
            
            return [self._dict_to_entity(topic_data) for topic_data in topics_data]
            
        except Exception as e:
            logger.error(f"❌ Failed to get all topics: {e}")
            return []
    
    def find_by_category(self, category: str, limit: int = 50) -> List[Topic]:
        """
        Find topics by category
        
        Args:
            category: Topic category
            limit: Maximum number of topics to return
            
        Returns:
            List of topic entities in the specified category
        """
        try:
            topics_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "is_active", "operator": "==", "value": True},
                    {"field": "category", "operator": "==", "value": category}
                ],
                limit=limit
                # Removed order_by to avoid composite index requirement
            )
            
            # Sort by name in application layer
            topics = [self._dict_to_entity(topic_data) for topic_data in topics_data]
            topics.sort(key=lambda x: x.name)
            
            return topics
            
        except Exception as e:
            logger.error(f"❌ Failed to find topics by category {category}: {e}")
            return []
    
    def find_by_difficulty_level(self, difficulty_level: int, limit: int = 50) -> List[Topic]:
        """
        Find topics by difficulty level
        
        Args:
            difficulty_level: Topic difficulty level (1-5)
            limit: Maximum number of topics to return
            
        Returns:
            List of topic entities with the specified difficulty level
        """
        try:
            topics_data = self.firebase.query_documents(
                self.collection_name,
                filters=[
                    {"field": "is_active", "operator": "==", "value": True},
                    {"field": "difficulty_level", "operator": "==", "value": difficulty_level}
                ],
                limit=limit
                # Removed order_by to avoid composite index requirement
            )
            
            # Sort by name in application layer
            topics = [self._dict_to_entity(topic_data) for topic_data in topics_data]
            topics.sort(key=lambda x: x.name)
            
            return topics
            
        except Exception as e:
            logger.error(f"❌ Failed to find topics by difficulty level {difficulty_level}: {e}")
            return []
    
    def update(self, topic: Topic) -> Topic:
        """
        Update topic in Firebase Firestore
        
        Args:
            topic: Topic entity to update
            
        Returns:
            Updated topic entity
        """
        try:
            topic_data = self._entity_to_dict(topic)
            
            # Remove ID from data (it's the document ID)
            topic_data.pop('id', None)
            
            # Update in Firestore
            self.firebase.update_document(
                self.collection_name,
                str(topic.id),
                topic_data
            )
            
            logger.info(f"✅ Topic updated successfully: {topic.id}")
            return topic
            
        except Exception as e:
            logger.error(f"❌ Failed to update topic {topic.id}: {e}")
            raise
    
    def delete(self, topic_id: UUID) -> None:
        """
        Delete topic from Firebase Firestore (soft delete)
        
        Args:
            topic_id: Topic's UUID
        """
        try:
            # Soft delete - mark as inactive
            self.firebase.update_document(
                self.collection_name,
                str(topic_id),
                {"is_active": False}
            )
            
            logger.info(f"✅ Topic deleted (soft) successfully: {topic_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete topic {topic_id}: {e}")
            raise
    
    def search_topics(self, query: str, limit: int = 20) -> List[Topic]:
        """
        Search topics by name or description
        
        Note: This is a simple implementation. For production, 
        consider using Elasticsearch or similar for full-text search.
        
        Args:
            query: Search query
            limit: Maximum number of topics to return
            
        Returns:
            List of topic entities matching the search query
        """
        try:
            # Simple search implementation
            # In production, you would use more sophisticated search
            all_topics = self.find_all_active(limit=1000)
            
            query_lower = query.lower()
            matching_topics = []
            
            for topic in all_topics:
                if (query_lower in topic.name.lower() or 
                    query_lower in topic.description.lower() or
                    any(query_lower in tag.lower() for tag in topic.tags)):
                    matching_topics.append(topic)
                    
                    if len(matching_topics) >= limit:
                        break
            
            return matching_topics
            
        except Exception as e:
            logger.error(f"❌ Failed to search topics with query '{query}': {e}")
            return []
    
    def get_popular_topics(self, limit: int = 10) -> List[Topic]:
        """
        Get most popular topics based on usage statistics
        
        Args:
            limit: Maximum number of topics to return
            
        Returns:
            List of popular topic entities
        """
        try:
            topics_data = self.firebase.query_documents(
                self.collection_name,
                filters=[{"field": "is_active", "operator": "==", "value": True}],
                limit=limit
                # Removed order_by to avoid composite index requirement
            )
            
            # Sort by total_matches in application layer (descending)
            topics = [self._dict_to_entity(topic_data) for topic_data in topics_data]
            topics.sort(key=lambda x: x.total_matches, reverse=True)
            
            return topics
            
        except Exception as e:
            logger.error(f"❌ Failed to get popular topics: {e}")
            return []
    
    def _entity_to_dict(self, topic: Topic) -> dict:
        """
        Convert topic entity to dictionary for Firestore
        
        Args:
            topic: Topic entity
            
        Returns:
            Dictionary representation
        """
        return {
            "id": str(topic.id),
            "name": topic.name,
            "description": topic.description,
            "category": topic.category,
            "difficulty_level": topic.difficulty_level,
            "is_active": topic.is_active,
            "created_at": topic.created_at.isoformat(),
            "tags": topic.tags,
            "total_matches": topic.total_matches,
            "total_rooms": topic.total_rooms,
            "average_rating": topic.average_rating
        }
    
    def _dict_to_entity(self, data: dict) -> Topic:
        """
        Convert dictionary to topic entity
        
        Args:
            data: Dictionary from Firestore
            
        Returns:
            Topic entity
        """
        from datetime import datetime
        
        return Topic(
            id=UUID(data["id"]),
            name=data["name"],
            description=data["description"],
            category=data["category"],
            difficulty_level=data["difficulty_level"],
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            tags=data.get("tags", []),
            total_matches=data.get("total_matches", 0),
            total_rooms=data.get("total_rooms", 0),
            average_rating=data.get("average_rating", 0.0)
        )
    
    def create_default_topics(self) -> None:
        """
        Create default topics for the application
        """
        default_topics = [
            {
                "name": "Technology",
                "description": "Discuss latest tech trends, programming, and innovation",
                "category": "Tech",
                "difficulty_level": 2,
                "tags": ["programming", "innovation", "startups", "AI", "web development"]
            },
            {
                "name": "Movies & Entertainment",
                "description": "Talk about favorite movies, shows, and entertainment",
                "category": "Entertainment",
                "difficulty_level": 1,
                "tags": ["movies", "tv shows", "netflix", "cinema", "actors"]
            },
            {
                "name": "Travel & Culture",
                "description": "Share travel experiences and cultural insights",
                "category": "Lifestyle",
                "difficulty_level": 2,
                "tags": ["travel", "culture", "food", "adventure", "countries"]
            },
            {
                "name": "Health & Fitness",
                "description": "Discuss health tips, fitness routines, and wellness",
                "category": "Health",
                "difficulty_level": 2,
                "tags": ["fitness", "nutrition", "mental health", "exercise", "wellness"]
            },
            {
                "name": "Business & Entrepreneurship",
                "description": "Talk about business ideas, entrepreneurship, and career growth",
                "category": "Business",
                "difficulty_level": 3,
                "tags": ["business", "startups", "career", "leadership", "investment"]
            },
            {
                "name": "Music & Arts",
                "description": "Discuss music, art, creativity, and artistic expression",
                "category": "Arts",
                "difficulty_level": 1,
                "tags": ["music", "art", "creativity", "instruments", "painting"]
            },
            {
                "name": "Science & Nature",
                "description": "Explore scientific discoveries and natural phenomena",
                "category": "Science",
                "difficulty_level": 3,
                "tags": ["science", "nature", "environment", "research", "discovery"]
            },
            {
                "name": "Gaming",
                "description": "Talk about video games, gaming culture, and esports",
                "category": "Gaming",
                "difficulty_level": 1,
                "tags": ["gaming", "esports", "video games", "streaming", "reviews"]
            }
        ]
        
        try:
            for topic_data in default_topics:
                topic = new_topic(
                    name=topic_data["name"],
                    description=topic_data["description"],
                    category=topic_data["category"],
                    difficulty_level=topic_data["difficulty_level"]
                )
                topic.tags = topic_data["tags"]
                
                # Check if topic already exists
                existing_topics = self.firebase.query_documents(
                    self.collection_name,
                    filters=[{"field": "name", "operator": "==", "value": topic.name}],
                    limit=1
                )
                
                if not existing_topics:
                    self.save(topic)
                    logger.info(f"✅ Created default topic: {topic.name}")
                else:
                    logger.info(f"⏩ Topic already exists: {topic.name}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to create default topics: {e}")
            raise 