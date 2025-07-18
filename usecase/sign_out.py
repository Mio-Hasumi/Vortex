# app/usecase/sign_out.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# ---------- 依赖端口 ---------- #
class AuthTokenService(Protocol):
    def revoke(self, token: str) -> None: ...


# ---------- DTO ---------- #
@dataclass(frozen=True)
class SignOutInput:
    auth_token: str


@dataclass(frozen=True)
class SignOutOutput:
    ok: bool = True


# ---------- 用例 ---------- #
class SignOutInteractor:
    """
    登出：使当前 token 失效（黑名单或删除）
    """

    def __init__(self, token_srv: AuthTokenService) -> None:
        self._tokens = token_srv

    def execute(self, inp: SignOutInput) -> SignOutOutput:
        self._tokens.revoke(inp.auth_token)
        return SignOutOutput()
