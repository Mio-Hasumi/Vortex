# app/usecase/start_call.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Protocol

from domain.entities import CallSession, new_session, CallStatus


# --------------------------------------------------------------------------- #
# 1. 依赖协议（Ports）
# --------------------------------------------------------------------------- #
class UserReader(Protocol):
    def exists(self, user_id: UUID) -> bool: ...


class CallSessionWriter(Protocol):
    def save(self, session: CallSession) -> None: ...


class LiveKitPort(Protocol):
    """
    与 LiveKit Server 交互所需的最小 API。
    由 interface/gateways/livekit_adapter.py 实现。
    """
    def create_room_if_not_exists(self, room_name: str) -> None: ...
    
    def build_access_token(
        self,
        room: str,
        identity: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str: ...


# --------------------------------------------------------------------------- #
# 2. 输入 / 输出 DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StartCallInput:
    user_a_id: UUID
    room_name: str | None = None         # 可允许前端指定；不填则生成 UUID


@dataclass(frozen=True)
class StartCallOutput:
    session_id: UUID
    room_name: str
    token_user_a: str
    token_host: str


# --------------------------------------------------------------------------- #
# 3. 用例实现
# --------------------------------------------------------------------------- #
class StartCallInteractor:
    """
    ***用例：发起一次“AI + User A”通话***
    步骤：
      1) 校验 User A 是否存在
      2) 建立 CallSession 实体
      3) 在 LiveKit Cloud 创建房间（如需）
      4) 为用户 & AI 生成 Token
      5) 持久化 Session，返回 DTO
    """

    HOST_ID_PREFIX = "host_"

    def __init__(
        self,
        user_reader: UserReader,
        session_writer: CallSessionWriter,
        livekit: LiveKitPort,
    ) -> None:
        self._users = user_reader
        self._sessions = session_writer
        self._lk = livekit

    # ---------- 业务入口 ----------
    def execute(self, inp: StartCallInput) -> StartCallOutput:
        # 1. 校验用户
        if not self._users.exists(inp.user_a_id):
            raise ValueError(f"User {inp.user_a_id} not found")

        # 2. 生成房间名 & Host identity
        room_name = inp.room_name or f"room-{uuid4().hex[:8]}"
        host_identity = f"{self.HOST_ID_PREFIX}{uuid4().hex[:6]}"

        # 3. 创建 CallSession 实体 (领域对象)
        session = new_session(
            room_name=room_name,
            host_identity=host_identity,
            user_a_id=inp.user_a_id,
        )

        # 4. LiveKit 操作
        self._lk.create_room_if_not_exists(room_name)

        token_user_a = self._lk.build_access_token(
            room=room_name,
            identity=str(inp.user_a_id),
            can_publish=True,
            can_subscribe=True,
        )
        token_host = self._lk.build_access_token(
            room=room_name,
            identity=host_identity,
            can_publish=True,      # AI 需要发声
            can_subscribe=True,
        )

        # 5. 持久化
        self._sessions.save(session)

        # 6. 返回结果 DTO
        return StartCallOutput(
            session_id=session.id,
            room_name=room_name,
            token_user_a=token_user_a,
            token_host=token_host,
        )
