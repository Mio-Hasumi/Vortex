# app/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


# Status Enums
class CallStatus(Enum):
    """Lifecycle Enum: Waiting ➜ In Call ➜ Ended"""
    WAITING = auto()
    ACTIVE = auto()
    ENDED = auto()


class RoomStatus(Enum):
    """Multi-user Chat Room Status"""
    WAITING = auto()      # Waiting for participants
    ACTIVE = auto()       # Active chat
    PAUSED = auto()       # Paused
    ENDED = auto()        # Ended


class MatchStatus(Enum):
    """Match Status"""
    PENDING = auto()      # Waiting for match
    MATCHED = auto()      # Match successful
    CANCELLED = auto()    # Match cancelled
    EXPIRED = auto()      # Match expired


class FriendshipStatus(Enum):
    """Friendship Status"""
    PENDING = auto()      # Pending confirmation
    ACCEPTED = auto()     # Accepted
    REJECTED = auto()     # Rejected
    BLOCKED = auto()      # Blocked


class RecordingStatus(Enum):
    """Recording Status"""
    PROCESSING = auto()   # Processing
    READY = auto()        # Ready
    FAILED = auto()       # Processing failed


class UserStatus(Enum):
    """User Online Status"""
    ONLINE = auto()
    OFFLINE = auto()
    IN_CALL = auto()


# Domain Entities
@dataclass
class User:
    """
    Domain entity: Platform User
    """
    id: UUID
    display_name: str
    firebase_uid: str  # Firebase Auth UID - Used for Firebase ID Token verification
    password_hash: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    push_token: Optional[str] = None    # APNs / FCM token
    status: UserStatus = UserStatus.OFFLINE
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    preferred_language: str = "en"
    
    # Topic preferences for matching
    topic_preferences: List[str] = field(default_factory=list)
    interest_levels: Dict[str, int] = field(default_factory=dict)  # topic_id -> interest_level (1-5)
    
    # AI preferences
    ai_enabled: bool = False  # Whether AI processing is enabled for this user (starts disabled)

    def update_status(self, status: UserStatus) -> None:
        """Update user status"""
        self.status = status
        if status == UserStatus.OFFLINE:
            self.last_seen = datetime.now(timezone.utc)


@dataclass
class Topic:
    """
    Topic entity - Used for matching and chatting
    """
    id: UUID
    name: str
    description: str
    category: str
    difficulty_level: int  # Difficulty level 1-5
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    
    # Statistics
    total_matches: int = 0
    total_rooms: int = 0
    average_rating: float = 0.0


@dataclass
class Room:
    """
    Multi-user Voice Chat Room (extends original CallSession)
    """
    id: UUID
    name: str
    topic_id: UUID
    livekit_room_name: str
    host_ai_identity: str             # AI host identity in LiveKit
    created_by: UUID  # Creator ID
    max_participants: int = 10
    current_participants: List[UUID] = field(default_factory=list)
    status: RoomStatus = RoomStatus.WAITING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    is_private: bool = False
    
    # Recording settings
    is_recording_enabled: bool = True
    recording_id: Optional[UUID] = None

    # Domain behaviors
    def add_participant(self, user_id: UUID) -> None:
        """Add participant"""
        if len(self.current_participants) >= self.max_participants:
            raise ValueError("Room is full")
        
        if user_id not in self.current_participants:
            self.current_participants.append(user_id)
            
        # If it's the first participant, activate the room
        if len(self.current_participants) == 1 and self.status == RoomStatus.WAITING:
            self.start()

    def remove_participant(self, user_id: UUID) -> None:
        """Remove participant"""
        if user_id in self.current_participants:
            self.current_participants.remove(user_id)
            
        # If there are no participants left, end the room
        if len(self.current_participants) == 0:
            self.end()

    def start(self) -> None:
        """Start chat"""
        if self.status != RoomStatus.WAITING:
            raise ValueError("Room cannot be started")
        
        self.status = RoomStatus.ACTIVE
        self.started_at = datetime.now(timezone.utc)

    def end(self) -> None:
        """End chat"""
        if self.status == RoomStatus.ENDED:
            return
            
        self.status = RoomStatus.ENDED
        self.ended_at = datetime.now(timezone.utc)
        self.current_participants.clear()

    def pause(self) -> None:
        """Pause chat"""
        if self.status == RoomStatus.ACTIVE:
            self.status = RoomStatus.PAUSED

    def resume(self) -> None:
        """Resume chat"""
        if self.status == RoomStatus.PAUSED:
            self.status = RoomStatus.ACTIVE


@dataclass
class Match:
    """
    Match entity - User matching system
    """
    id: UUID
    user_id: UUID
    preferred_topics: List[UUID]
    max_participants: int = 3
    language_preference: Optional[str] = None
    status: MatchStatus = MatchStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    matched_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # Matching results
    matched_users: List[UUID] = field(default_factory=list)
    selected_topic_id: Optional[UUID] = None
    room_id: Optional[UUID] = None
    
    queue_position: int = 0
    estimated_wait_time: int = 0  # seconds

    def mark_as_matched(self, matched_users: List[UUID], topic_id: UUID, room_id: UUID) -> None:
        """Mark as matched"""
        if self.status != MatchStatus.PENDING:
            raise ValueError("Match is not in pending status")
            
        self.status = MatchStatus.MATCHED
        self.matched_at = datetime.now(timezone.utc)
        self.matched_users = matched_users
        self.selected_topic_id = topic_id
        self.room_id = room_id

    def cancel(self) -> None:
        """Cancel match"""
        if self.status == MatchStatus.PENDING:
            self.status = MatchStatus.CANCELLED

    def expire(self) -> None:
        """Mark as expired"""
        if self.status == MatchStatus.PENDING:
            self.status = MatchStatus.EXPIRED
            self.expired_at = datetime.now(timezone.utc)


@dataclass
class Friendship:
    """
    Friendship entity
    """
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: FriendshipStatus = FriendshipStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    message: Optional[str] = None  # Friendship request message
    
    def accept(self) -> None:
        """Accept friendship request"""
        if self.status != FriendshipStatus.PENDING:
            raise ValueError("Friendship is not in pending status")
            
        self.status = FriendshipStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        """Reject friendship request"""
        if self.status != FriendshipStatus.PENDING:
            raise ValueError("Friendship is not in pending status")
            
        self.status = FriendshipStatus.REJECTED

    def block(self) -> None:
        """Block user"""
        self.status = FriendshipStatus.BLOCKED


@dataclass
class Recording:
    """
    Recording entity
    """
    id: UUID
    room_id: UUID
    file_path: str  # Storage path
    file_size: int  # bytes
    duration: int   # seconds
    status: RecordingStatus = RecordingStatus.PROCESSING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    
    # Participants info
    participants: List[UUID] = field(default_factory=list)
    
    # Download and sharing
    download_count: int = 0
    share_token: Optional[str] = None
    share_expires_at: Optional[datetime] = None

    def mark_as_ready(self) -> None:
        """Mark as ready"""
        self.status = RecordingStatus.READY
        self.processed_at = datetime.now(timezone.utc)

    def mark_as_failed(self) -> None:
        """Mark as failed"""
        self.status = RecordingStatus.FAILED
        self.processed_at = datetime.now(timezone.utc)

    def generate_share_token(self, expires_in_hours: int = 24) -> str:
        """Generate share token"""
        import secrets
        self.share_token = secrets.token_urlsafe(32)
        self.share_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        return self.share_token

    def increment_download_count(self) -> None:
        """Increment download count"""
        self.download_count += 1


@dataclass
class Transcript:
    """
    Call transcript (supports multiple participants)
    """
    id: UUID
    room_id: UUID
    speaker_id: UUID               # Speaker ID
    speaker_type: str              # "user" / "ai_host"
    text: str
    confidence: float = 1.0        # Transcription confidence
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    start_time: float = 0.0        # Start time in recording (seconds)
    end_time: float = 0.0          # End time in recording (seconds)
    
    # Language detection
    detected_language: Optional[str] = None
    
    # Sentiment analysis
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None  # positive, negative, neutral


@dataclass
class Message:
    """
    Chat message entity (supports text and audio)
    """
    id: UUID
    room_id: UUID
    sender_id: UUID
    sender_type: str               # "user" / "ai_host"
    message_type: str              # "text" / "audio" / "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Audio message specific
    audio_url: Optional[str] = None
    audio_duration: Optional[int] = None  # seconds
    
    # System message specific
    system_event: Optional[str] = None  # "user_joined", "user_left", "room_started", etc.
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIHostSession:
    """
    AI Host Session State
    """
    id: UUID
    room_id: UUID
    topic_id: UUID
    conversation_state: str = "greeting"  # greeting, discussion, conclusion
    conversation_context: List[Dict[str, Any]] = field(default_factory=list)
    
    # Conversation statistics
    total_exchanges: int = 0
    active_participants: List[UUID] = field(default_factory=list)
    
    # AI behavior settings
    personality_type: str = "friendly"  # friendly, professional, casual
    engagement_level: int = 5  # 1-10 scale
    
    # Conversation management
    last_ai_message_at: Optional[datetime] = None
    next_intervention_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_exchange(self, user_id: UUID, user_message: str, ai_response: str) -> None:
        """Add conversation exchange"""
        self.total_exchanges += 1
        self.conversation_context.append({
            "user_id": str(user_id),
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc)

    def update_conversation_state(self, new_state: str) -> None:
        """Update conversation state"""
        self.conversation_state = new_state
        self.updated_at = datetime.now(timezone.utc)


# Factory functions for creating entities
def new_user(display_name: str, email: Optional[str] = None, phone_number: Optional[str] = None, password_hash: str = "", firebase_uid: str = "") -> User:
    return User(
        id=uuid4(),
        display_name=display_name,
        firebase_uid=firebase_uid,
        password_hash=password_hash,
        email=email,
        phone_number=phone_number,
        ai_enabled=False  # AI starts disabled by default
    )


def new_topic(name: str, description: str, category: str, difficulty_level: int) -> Topic:
    return Topic(
        id=uuid4(),
        name=name,
        description=description,
        category=category,
        difficulty_level=difficulty_level
    )


def new_room(name: str, topic_id: UUID, created_by: UUID, max_participants: int = 10) -> Room:
    room_id = uuid4()
    return Room(
        id=room_id,
        name=name,
        topic_id=topic_id,
        livekit_room_name=f"room_{room_id}",
        host_ai_identity=f"ai_host_{room_id}",
        max_participants=max_participants,
        created_by=created_by
    )


def new_match(user_id: UUID, preferred_topics: List[UUID], max_participants: int = 3) -> Match:
    return Match(
        id=uuid4(),
        user_id=user_id,
        preferred_topics=preferred_topics,
        max_participants=max_participants
    )


def new_friendship(user_id: UUID, friend_id: UUID, message: Optional[str] = None) -> Friendship:
    return Friendship(
        id=uuid4(),
        user_id=user_id,
        friend_id=friend_id,
        message=message
    )


def new_recording(room_id: UUID, file_path: str, participants: List[UUID]) -> Recording:
    return Recording(
        id=uuid4(),
        room_id=room_id,
        file_path=file_path,
        file_size=0,  # Will be set after processing
        duration=0,   # Will be set after processing
        participants=participants
    )


def new_ai_host_session(room_id: UUID, topic_id: UUID) -> AIHostSession:
    return AIHostSession(
        id=uuid4(),
        room_id=room_id,
        topic_id=topic_id
    )


# Legacy support - keeping old CallSession for backward compatibility
@dataclass
class CallSession:
    """
    Legacy: Three-party call session (AI + A + B)
    Maintains backward compatibility
    """
    id: UUID
    room_name: str
    host_identity: str
    user_a_id: UUID
    user_b_id: Optional[UUID] = None
    status: CallStatus = CallStatus.WAITING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    def activate(self, user_b_id: UUID) -> None:
        """Called when B successfully joins"""
        if self.status is not CallStatus.WAITING:
            raise ValueError("Session already activated or ended")
        self.user_b_id = user_b_id
        self.status = CallStatus.ACTIVE

    def end(self) -> None:
        """End session and timestamp"""
        if self.status is CallStatus.ENDED:
            return
        self.status = CallStatus.ENDED
        self.ended_at = datetime.now(timezone.utc)


def new_session(room_name: str, host_identity: str, user_a_id: UUID) -> CallSession:
    """Legacy factory function"""
    return CallSession(
        id=uuid4(),
        room_name=room_name,
        host_identity=host_identity,
        user_a_id=user_a_id,
    )
