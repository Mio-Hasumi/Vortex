# app/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


# Status Enums
class CallStatus(Enum):
    """生命周期枚举：等待 ➜ 通话中 ➜ 结束"""
    WAITING = auto()
    ACTIVE = auto()
    ENDED = auto()


class RoomStatus(Enum):
    """多人聊天室状态"""
    WAITING = auto()      # 等待参与者
    ACTIVE = auto()       # 活跃聊天中
    PAUSED = auto()       # 暂停
    ENDED = auto()        # 结束


class MatchStatus(Enum):
    """匹配状态"""
    PENDING = auto()      # 等待匹配
    MATCHED = auto()      # 匹配成功
    CANCELLED = auto()    # 取消匹配
    EXPIRED = auto()      # 匹配过期


class FriendshipStatus(Enum):
    """好友关系状态"""
    PENDING = auto()      # 待确认
    ACCEPTED = auto()     # 已接受
    REJECTED = auto()     # 已拒绝
    BLOCKED = auto()      # 已拉黑


class RecordingStatus(Enum):
    """录音状态"""
    PROCESSING = auto()   # 处理中
    READY = auto()        # 准备就绪
    FAILED = auto()       # 处理失败


class UserStatus(Enum):
    """用户在线状态"""
    ONLINE = auto()
    OFFLINE = auto()
    IN_CALL = auto()


# Domain Entities
@dataclass
class User:
    """
    Domain entity: 平台用户
    """
    id: UUID
    display_name: str
    email: str
    firebase_uid: str  # Firebase Auth UID - 用于Firebase ID Token验证
    password_hash: str
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

    def update_status(self, status: UserStatus) -> None:
        """更新用户状态"""
        self.status = status
        if status == UserStatus.OFFLINE:
            self.last_seen = datetime.now(timezone.utc)


@dataclass
class Topic:
    """
    话题实体 - 用于匹配和聊天
    """
    id: UUID
    name: str
    description: str
    category: str
    difficulty_level: int  # 1-5 难度等级
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
    多人语音聊天室 (扩展原CallSession)
    """
    id: UUID
    name: str
    topic_id: UUID
    livekit_room_name: str
    host_ai_identity: str             # AI主持人在LiveKit中的identity
    created_by: UUID  # 创建者ID
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
        """添加参与者"""
        if len(self.current_participants) >= self.max_participants:
            raise ValueError("Room is full")
        
        if user_id not in self.current_participants:
            self.current_participants.append(user_id)
            
        # 如果是第一个参与者，激活房间
        if len(self.current_participants) == 1 and self.status == RoomStatus.WAITING:
            self.start()

    def remove_participant(self, user_id: UUID) -> None:
        """移除参与者"""
        if user_id in self.current_participants:
            self.current_participants.remove(user_id)
            
        # 如果没有参与者了，结束房间
        if len(self.current_participants) == 0:
            self.end()

    def start(self) -> None:
        """开始聊天"""
        if self.status != RoomStatus.WAITING:
            raise ValueError("Room cannot be started")
        
        self.status = RoomStatus.ACTIVE
        self.started_at = datetime.now(timezone.utc)

    def end(self) -> None:
        """结束聊天"""
        if self.status == RoomStatus.ENDED:
            return
            
        self.status = RoomStatus.ENDED
        self.ended_at = datetime.now(timezone.utc)
        self.current_participants.clear()

    def pause(self) -> None:
        """暂停聊天"""
        if self.status == RoomStatus.ACTIVE:
            self.status = RoomStatus.PAUSED

    def resume(self) -> None:
        """恢复聊天"""
        if self.status == RoomStatus.PAUSED:
            self.status = RoomStatus.ACTIVE


@dataclass
class Match:
    """
    匹配实体 - 用户匹配系统
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
    
    # Queue position
    queue_position: int = 0
    estimated_wait_time: int = 0  # seconds

    def mark_as_matched(self, matched_users: List[UUID], topic_id: UUID, room_id: UUID) -> None:
        """标记为匹配成功"""
        if self.status != MatchStatus.PENDING:
            raise ValueError("Match is not in pending status")
            
        self.status = MatchStatus.MATCHED
        self.matched_at = datetime.now(timezone.utc)
        self.matched_users = matched_users
        self.selected_topic_id = topic_id
        self.room_id = room_id

    def cancel(self) -> None:
        """取消匹配"""
        if self.status == MatchStatus.PENDING:
            self.status = MatchStatus.CANCELLED

    def expire(self) -> None:
        """标记为过期"""
        if self.status == MatchStatus.PENDING:
            self.status = MatchStatus.EXPIRED
            self.expired_at = datetime.now(timezone.utc)


@dataclass
class Friendship:
    """
    好友关系实体
    """
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: FriendshipStatus = FriendshipStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    message: Optional[str] = None  # 好友申请消息
    
    def accept(self) -> None:
        """接受好友申请"""
        if self.status != FriendshipStatus.PENDING:
            raise ValueError("Friendship is not in pending status")
            
        self.status = FriendshipStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        """拒绝好友申请"""
        if self.status != FriendshipStatus.PENDING:
            raise ValueError("Friendship is not in pending status")
            
        self.status = FriendshipStatus.REJECTED

    def block(self) -> None:
        """拉黑用户"""
        self.status = FriendshipStatus.BLOCKED


@dataclass
class Recording:
    """
    录音实体
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
        """标记为处理完成"""
        self.status = RecordingStatus.READY
        self.processed_at = datetime.now(timezone.utc)

    def mark_as_failed(self) -> None:
        """标记为处理失败"""
        self.status = RecordingStatus.FAILED
        self.processed_at = datetime.now(timezone.utc)

    def generate_share_token(self, expires_in_hours: int = 24) -> str:
        """生成分享token"""
        import secrets
        self.share_token = secrets.token_urlsafe(32)
        self.share_expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        return self.share_token

    def increment_download_count(self) -> None:
        """增加下载次数"""
        self.download_count += 1


@dataclass
class Transcript:
    """
    通话逐句转录 (扩展支持多人)
    """
    id: UUID
    room_id: UUID
    speaker_id: UUID               # 说话者ID
    speaker_type: str              # "user" / "ai_host"
    text: str
    confidence: float = 1.0        # 转录置信度
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    start_time: float = 0.0        # 在录音中的开始时间(秒)
    end_time: float = 0.0          # 在录音中的结束时间(秒)
    
    # Language detection
    detected_language: Optional[str] = None
    
    # Sentiment analysis
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None  # positive, negative, neutral


@dataclass
class Message:
    """
    聊天消息实体 (支持文本和语音)
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
    AI主持人会话状态
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
        """添加对话交换"""
        self.total_exchanges += 1
        self.conversation_context.append({
            "user_id": str(user_id),
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc)

    def update_conversation_state(self, new_state: str) -> None:
        """更新对话状态"""
        self.conversation_state = new_state
        self.updated_at = datetime.now(timezone.utc)


# Factory functions for creating entities
def new_user(display_name: str, email: str, password_hash: str, firebase_uid: str = "") -> User:
    return User(
        id=uuid4(),
        display_name=display_name,
        email=email,
        firebase_uid=firebase_uid,
        password_hash=password_hash
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
    Legacy: 一次三方通话会话（AI + A + B）
    保持向后兼容性
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
        """当B成功加入时调用"""
        if self.status is not CallStatus.WAITING:
            raise ValueError("Session already activated or ended")
        self.user_b_id = user_b_id
        self.status = CallStatus.ACTIVE

    def end(self) -> None:
        """结束会话并打时间戳"""
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
