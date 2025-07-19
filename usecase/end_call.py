

# app/usecase/end_call.py
from __future__ import annotations

"""
Use Case: EndCallInteractor
---------------------------------
  * Called by controller / Webhook when a three-party call ends
  * Responsibilities:
      1. Load CallSession
      2. Mark it as ENDED (if not already ended)
      3. Persist
      4. Call LiveKit to delete room (optional; can be skipped if Cloud auto-cleans)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID

from domain.entities import CallSession, CallStatus
# transcripts may be written by other processes; this use case remains lightweight and does not handle text


# --------------------------------------------------------------------------- #
# 1. Dependency Ports
# --------------------------------------------------------------------------- #
class CallSessionReader(Protocol):
    def by_id(self, session_id: UUID) -> CallSession | None: ...


class CallSessionWriter(Protocol):
    def save(self, session: CallSession) -> None: ...


class LiveKitPort(Protocol):
    def delete_room(self, room_name: str) -> None: ...


# --------------------------------------------------------------------------- #
# 2. Input / Output DTO
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EndCallInput:
    session_id: UUID
    hard_delete_room: bool = False     # Whether to force call LiveKit to delete room


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
# 4. Use Case Implementation
# --------------------------------------------------------------------------- #
class EndCallInteractor(EndCallUseCase):
    """
    End the call; if hard_delete_room=True, call LiveKitPort.delete_room.
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

    # ---------- Business Entry ----------
    def execute(self, inp: EndCallInput) -> EndCallOutput:
        session = self._sessions.by_id(inp.session_id)
        if not session:
            raise ValueError("CallSession not found")

        # Idempotent handling if already ended
        if session.status is not CallStatus.ENDED:
            session.end()
            self._save_session.save(session)

        # Room cleanup
        room_deleted = False
        if inp.hard_delete_room:
            try:
                self._lk.delete_room(session.room_name)
                room_deleted = True
            except Exception:
                # Cloud may have auto-cleaned; ignore 404
                room_deleted = False

        return EndCallOutput(
            session_id=session.id,
            room_deleted=room_deleted,
        )
