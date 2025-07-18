

# app/usecase/invite_user.py
from __future__ import annotations

"""
用例：InviteUserInteractor
    当 AI 主持人决定拉第二位用户进入房间时调用。
    职责：
        1. 读取 CallSession
        2. 依据 InvitationPolicy 校验是否允许邀请
        3. 生成 User B 的 LiveKit Token
        4. 更新 CallSession 状态并持久化
        5. 通过通知网关向 User B 发送邀请
"""

from dataclasses import dataclass
from uuid import UUID
from typing import Protocol, runtime_checkable

from domain.entities import CallSession, CallStatus
from domain.policies import InvitationPolicy


# --------------------------------------------------------------------------- #
# 1. 依赖端口（Ports）
# --------------------------------------------------------------------------- #
class CallSessionReader(Protocol):
    def by_id(self, session_id: UUID) -> CallSession | None: ...


class CallSessionWriter(Protocol):
    def save(self, session: CallSession) -> None: ...


class LiveKitPort(Protocol):
    def build_access_token(
        self,
        room: str,
        identity: str,
        can_publish: bool,
        can_subscribe: bool,
    ) -> str: ...


class NotificationGateway(Protocol):
    def push_invite(self, user_id: UUID, room: str, token: str) -> None: ...


# --------------------------------------------------------------------------- #
# 2. 输入 / 输出 DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InviteUserInput:
    session_id: UUID
    user_b_id: UUID
    exchanges_count: int = 0   # 已发生的对话往返次数，可由 HostAgent 统计
    reason: str | None = None


@dataclass(frozen=True)
class InviteUserOutput:
    token_user_b: str
    room_name: str


# --------------------------------------------------------------------------- #
# 3. Use‑Case Interface
# --------------------------------------------------------------------------- #
@runtime_checkable
class InviteUserUseCase(Protocol):
    def execute(self, inp: InviteUserInput) -> InviteUserOutput: ...


# --------------------------------------------------------------------------- #
# 4. 用例实现
# --------------------------------------------------------------------------- #
class InviteUserInteractor(InviteUserUseCase):
    """
    执行拉人逻辑；若策略不允许或 session 状态不合法，将抛出 ValueError。
    """

    def __init__(
        self,
        session_reader: CallSessionReader,
        session_writer: CallSessionWriter,
        livekit: LiveKitPort,
        notifier: NotificationGateway,
        policy: InvitationPolicy | None = None,
    ) -> None:
        self._sessions = session_reader
        self._save_session = session_writer
        self._lk = livekit
        self._notify = notifier
        self._policy = policy or InvitationPolicy()

    # ---------- 业务入口 ----------
    def execute(self, inp: InviteUserInput) -> InviteUserOutput:
        # 1. 读取会话
        session = self._sessions.by_id(inp.session_id)
        if not session:
            raise ValueError("CallSession not found")

        # 2. 校验状态
        if session.status is not CallStatus.WAITING:
            raise ValueError("Session already active or ended")

        # 3. 业务策略校验
        if not self._policy.can_invite(session, exchanges_count=inp.exchanges_count):
            raise ValueError("Invitation policy disallows inviting user now")

        # 4. 生成 LiveKit Token
        token = self._lk.build_access_token(
            room=session.room_name,
            identity=str(inp.user_b_id),
            can_publish=True,
            can_subscribe=True,
        )

        # 5. 更新会话实体并持久化
        session.activate(inp.user_b_id)
        self._save_session.save(session)

        # 6. 发送推送/邀请
        self._notify.push_invite(
            user_id=inp.user_b_id,
            room=session.room_name,
            token=token,
        )

        # 7. 返回 DTO
        return InviteUserOutput(
            token_user_b=token,
            room_name=session.room_name,
        )
