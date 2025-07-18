

# app/usecase/end_call.py
from __future__ import annotations

"""
用例：EndCallInteractor
---------------------------------
  * 当三方通话结束时，由控制器 / Webhook 调用
  * 职责：
      1. 加载 CallSession
      2. 将其标记为 ENDED（若尚未结束）
      3. 持久化
      4. 调用 LiveKit 删除房间（可选；若 Cloud 自动清理，可跳过）
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID

from domain.entities import CallSession, CallStatus
# transcripts 可能由其它流程写入；此用例保持轻量，不处理文本


# --------------------------------------------------------------------------- #
# 1. 依赖端口（Ports）
# --------------------------------------------------------------------------- #
class CallSessionReader(Protocol):
    def by_id(self, session_id: UUID) -> CallSession | None: ...


class CallSessionWriter(Protocol):
    def save(self, session: CallSession) -> None: ...


class LiveKitPort(Protocol):
    def delete_room(self, room_name: str) -> None: ...


# --------------------------------------------------------------------------- #
# 2. 输入 / 输出 DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EndCallInput:
    session_id: UUID
    hard_delete_room: bool = False     # 是否强制调用 LiveKit 删除房间


@dataclass(frozen=True)
class EndCallOutput:
    session_id: UUID
    room_deleted: bool


# --------------------------------------------------------------------------- #
# 3. Use-Case Interface
# --------------------------------------------------------------------------- #
@runtime_checkable
class EndCallUseCase(Protocol):
    def execute(self, inp: EndCallInput) -> EndCallOutput: ...


# --------------------------------------------------------------------------- #
# 4. 用例实现
# --------------------------------------------------------------------------- #
class EndCallInteractor(EndCallUseCase):
    """
    结束通话；若 hard_delete_room=True 则调用 LiveKitPort.delete_room。
    """

    def __init__(
        self,
        session_reader: CallSessionReader,
        session_writer: CallSessionWriter,
        livekit: LiveKitPort,
    ) -> None:
        self._sessions = session_reader
        self._save_session = session_writer
        self._lk = livekit

    # ---------- 业务入口 ----------
    def execute(self, inp: EndCallInput) -> EndCallOutput:
        session = self._sessions.by_id(inp.session_id)
        if not session:
            raise ValueError("CallSession not found")

        # 若已结束则幂等化处理
        if session.status is not CallStatus.ENDED:
            session.end()
            self._save_session.save(session)

        # 房间清理
        room_deleted = False
        if inp.hard_delete_room:
            try:
                self._lk.delete_room(session.room_name)
                room_deleted = True
            except Exception:
                # Cloud 可能已自动清理；忽略 404
                room_deleted = False

        return EndCallOutput(
            session_id=session.id,
            room_deleted=room_deleted,
        )
