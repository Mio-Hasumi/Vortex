

# app/usecase/invite_user.py
from __future__ import annotations

"""
Use Case: InviteUserInteractor
    Called when the AI host decides to bring a second user into the room.
    Responsibilities:
        1. Read CallSession
        2. Check if invitation is allowed based on InvitationPolicy
        3. Generate LiveKit Token for User B
        4. Update CallSession status and persist
        5. Send invitation to User B via Notification Gateway
"""

from dataclasses import dataclass
from uuid import UUID
from typing import Protocol, runtime_checkable

from domain.entities import CallSession, CallStatus
from domain.policies import InvitationPolicy


# --------------------------------------------------------------------------- #
# 1. Dependency Ports
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
# 2. Input / Output DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InviteUserInput:
    session_id: UUID
    user_b_id: UUID
    exchanges_count: int = 0   # Number of dialogue exchanges that have occurred, can be tracked by HostAgent
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
# 4. Use Case Implementation
# --------------------------------------------------------------------------- #
class InviteUserInteractor(InviteUserUseCase):
    """
    Execute the logic to invite a user; if the policy does not allow or the session status is invalid, a ValueError will be raised.
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

    # ---------- Business Entry ----------
    def execute(self, inp: InviteUserInput) -> InviteUserOutput:
        # 1. Read session
        session = self._sessions.by_id(inp.session_id)
        if not session:
            raise ValueError("CallSession not found")

        # 2. Validate status
        if session.status is not CallStatus.WAITING:
            raise ValueError("Session already active or ended")

        # 3. Business policy validation
        if not self._policy.can_invite(session, exchanges_count=inp.exchanges_count):
            raise ValueError("Invitation policy disallows inviting user now")

        # 4. Generate LiveKit Token
        token = self._lk.build_access_token(
            room=session.room_name,
            identity=str(inp.user_b_id),
            can_publish=True,
            can_subscribe=True,
        )

        # 5. Update session entity and persist
        session.activate(inp.user_b_id)
        self._save_session.save(session)

        # 6. Send push/invitation
        self._notify.push_invite(
            user_id=inp.user_b_id,
            room=session.room_name,
            token=token,
        )

        # 7. Return DTO
        return InviteUserOutput(
            token_user_b=token,
            room_name=session.room_name,
        )
