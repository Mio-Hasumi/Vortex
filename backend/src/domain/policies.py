"""
Business Policy: Separate pure business rules like "When can AI invite a second user"
from the framework/infrastructure to facilitate unit testing and evolution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .entities import CallSession, CallStatus


class InvitationPolicy:
    """
    Compliance check before AI triggers the invite_user tool
    -------------------------------------------------
    * Wait at least MIN_EXCHANGES rounds of conversation, or
    * Wait for more than MAX_WAIT_SECONDS seconds
    """
    MIN_EXCHANGES: int = 4
    MAX_WAIT_SECONDS: int = 300  # 5 minutes

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        # Allows injection of a fake clock for testing
        self._now = clock or (lambda: datetime.now(timezone.utc))

    # ---------- Rule Entry ----------
    def can_invite(
        self,
        session: CallSession,
        exchanges_count: int,
    ) -> bool:
        """
        Args:
            session: Current call session
            exchanges_count: Number of exchanges completed between A and AI
        Returns:
            True  => HostAgent can call invite_user()
            False => Cannot invite yet
        """
        if session.status is not CallStatus.WAITING:
            return False

        if exchanges_count >= self.MIN_EXCHANGES:
            return True

        elapsed = (self._now() - session.started_at).total_seconds()
        return elapsed >= self.MAX_WAIT_SECONDS
