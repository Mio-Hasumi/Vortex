# app/usecase/start_call.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Protocol

from domain.entities import CallSession, new_session, CallStatus


# --------------------------------------------------------------------------- #
# 1. Dependency Protocols (Ports)
# --------------------------------------------------------------------------- #
class UserReader(Protocol):
    def exists(self, user_id: UUID) -> bool: ...


class CallSessionWriter(Protocol):
    def save(self, session: CallSession) -> None: ...


class LiveKitPort(Protocol):
    """
    Minimum API required to interact with LiveKit Server.
    Implemented by interface/gateways/livekit_adapter.py.
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
# 2. Input / Output DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StartCallInput:
    user_a_id: UUID
    room_name: str | None = None         # Can be specified by the frontend; if not provided, a UUID will be generated


@dataclass(frozen=True)
class StartCallOutput:
    session_id: UUID
    room_name: str
    token_user_a: str
    token_host: str


# --------------------------------------------------------------------------- #
# 3. Use Case Implementation
# --------------------------------------------------------------------------- #
class StartCallInteractor:
    """
    ***Use Case: Initiate an "AI + User A" Call***
    Steps:
      1) Validate if User A exists
      2) Create CallSession entity
      3) Create room in LiveKit Cloud (if needed)
      4) Generate Tokens for User & AI
      5) Persist Session and return DTO
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

    # ---------- Business Entry ----------
    def execute(self, inp: StartCallInput) -> StartCallOutput:
        # 1. Validate user
        if not self._users.exists(inp.user_a_id):
            raise ValueError(f"User {inp.user_a_id} not found")

        # 2. Generate room name & Host identity
        room_name = inp.room_name or f"room-{uuid4().hex[:8]}"
        host_identity = f"{self.HOST_ID_PREFIX}{uuid4().hex[:6]}"

        # 3. Create CallSession entity (domain object)
        session = new_session(
            room_name=room_name,
            host_identity=host_identity,
            user_a_id=inp.user_a_id,
        )

        # 4. LiveKit operations
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
            can_publish=True,      # AI needs to speak
            can_subscribe=True,
        )

        # 5. Persist
        self._sessions.save(session)

        # 6. Return result DTO
        return StartCallOutput(
            session_id=session.id,
            room_name=room_name,
            token_user_a=token_user_a,
            token_host=token_host,
        )
