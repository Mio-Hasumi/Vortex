# app/usecase/sign_in.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from typing import Protocol

from domain.entities import User


# ---------- 依赖端口 ---------- #
class UserRepository(Protocol):
    def find_by_email(self, email: str) -> User | None: ...
    def find_by_display_name(self, display_name: str) -> User | None: ...


class PasswordHasher(Protocol):
    def verify_password(self, plain_password: str, hashed_password: str) -> bool: ...


class AuthTokenService(Protocol):
    def create_access_token(self, user_id: UUID) -> str: ...
    def create_refresh_token(self, user_id: UUID) -> str: ...


class FirebaseAuthService(Protocol):
    def verify_id_token(self, id_token: str) -> dict: ...


# ---------- DTO ---------- #
@dataclass(frozen=True)
class SignInInput:
    email: str
    password: str


@dataclass(frozen=True)
class SignInOutput:
    user_id: UUID
    display_name: str
    email: str
    access_token: str
    refresh_token: str


# ---------- 用例 ---------- #
class SignInInteractor:
    """
    用户登录用例
    1) 验证输入数据
    2) 查找用户
    3) 验证密码
    4) 生成JWT令牌
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: AuthTokenService,
    ) -> None:
        self._user_repo = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, input_data: SignInInput) -> SignInOutput:
        # 1. 验证输入数据
        self._validate_input(input_data)
        
        # 2. 查找用户
        user = self._find_user(input_data.email)
        
        # 3. 验证密码
        if not self._password_hasher.verify_password(input_data.password, user.password_hash):
            raise ValueError("Invalid email or password")
        
        # 4. 生成JWT令牌
        access_token = self._token_service.create_access_token(user.id)
        refresh_token = self._token_service.create_refresh_token(user.id)
        
        return SignInOutput(
            user_id=user.id,
            display_name=user.display_name,
            email=user.email,
            access_token=access_token,
            refresh_token=refresh_token
        )

    def _validate_input(self, input_data: SignInInput) -> None:
        """验证输入数据"""
        if not input_data.email or not input_data.email.strip():
            raise ValueError("Email is required")
        
        if not self._is_valid_email(input_data.email):
            raise ValueError("Invalid email format")
        
        if not input_data.password:
            raise ValueError("Password is required")

    def _find_user(self, email: str) -> User:
        """查找用户"""
        user = self._user_repo.find_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        
        if not user.is_active:
            raise ValueError("User account is disabled")
        
        return user

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email.strip()) is not None
