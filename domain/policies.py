# app/domain/policies.py
"""
业务策略：把“什么时候 AI 可以邀请第二位用户”这种纯业务规则
与框架/基础设施剥离开，方便单测与演进。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .entities import CallSession, CallStatus


class InvitationPolicy:
    """
    AI 触发 invite_user 工具前的合规判断
    -------------------------------------------------
    * 至少等待 MIN_EXCHANGES 轮对话，或者
    * 已等待超过 MAX_WAIT_SECONDS 秒
    """
    MIN_EXCHANGES: int = 4
    MAX_WAIT_SECONDS: int = 300  # 5 分钟

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        # 方便测试时注入 fake clock
        self._now = clock or (lambda: datetime.now(timezone.utc))

    # ---------- 规则入口 ----------
    def can_invite(
        self,
        session: CallSession,
        exchanges_count: int,
    ) -> bool:
        """
        Args:
            session: 当前通话会话
            exchanges_count: A 与 AI 已完成的话语往返次数
        Returns:
            True  => HostAgent 可调用 invite_user()
            False => 暂不可邀请
        """
        if session.status is not CallStatus.WAITING:
            return False

        if exchanges_count >= self.MIN_EXCHANGES:
            return True

        elapsed = (self._now() - session.started_at).total_seconds()
        return elapsed >= self.MAX_WAIT_SECONDS
