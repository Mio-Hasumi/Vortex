# app/usecase/sign_up.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from typing import Protocol

from domain.entities import User, new_user


# ---------- 依赖端口 ---------- #
class UserRepository(Protocol):
    def save(self, user: User) -> User: ...
    def find_by_email(self, email: str) -> User | None: ...
    def find_by_display_name(self, display_name: str) -> User | None: ...


class PasswordHasher(Protocol):
    def hash_password(self, password: str) -> str: ...
    def validate_password_strength(self, password: str) -> dict[str, bool]: ...


class AuthTokenService(Protocol):
    def create_access_token(self, user_id: UUID) -> str: ...
    def create_refresh_token(self, user_id: UUID) -> str: ...


class FirebaseAuthService(Protocol):
    def create_user(self, email: str, password: str, display_name: str) -> dict: ...


# ---------- DTO ---------- #
@dataclass(frozen=True)
class SignUpInput:
    display_name: str
    email: str
    password: str


@dataclass(frozen=True)
class SignUpOutput:
    user_id: UUID
    display_name: str
    email: str
    access_token: str
    refresh_token: str


# ---------- 用例 ---------- #
class SignUpInteractor:
    """
    用户注册用例
    1) 验证输入数据
    2) 检查用户是否已存在
    3) 验证密码强度
    4) 创建Firebase用户
    5) 保存用户到数据库
    6) 生成JWT令牌
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: AuthTokenService,
        firebase_auth: FirebaseAuthService,
    ) -> None:
        self._user_repo = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._firebase_auth = firebase_auth

    def execute(self, input_data: SignUpInput) -> SignUpOutput:
        # 1. 验证输入数据
        self._validate_input(input_data)
        
        # 2. 检查用户是否已存在
        self._check_user_exists(input_data.email, input_data.display_name)
        
        # 3. 验证密码强度
        self._validate_password_strength(input_data.password)
        
        # 4. 创建Firebase用户
        firebase_user = self._firebase_auth.create_user(
            email=input_data.email,
            password=input_data.password,
            display_name=input_data.display_name
        )
        
        # 5. 哈希密码并创建用户实体
        hashed_password = self._password_hasher.hash_password(input_data.password)
        user = new_user(
            display_name=input_data.display_name,
            email=input_data.email,
            password_hash=hashed_password
        )
        
        # 6. 保存用户到数据库
        saved_user = self._user_repo.save(user)
        
        # 7. 生成JWT令牌
        access_token = self._token_service.create_access_token(saved_user.id)
        refresh_token = self._token_service.create_refresh_token(saved_user.id)
        
        return SignUpOutput(
            user_id=saved_user.id,
            display_name=saved_user.display_name,
            email=saved_user.email,
            access_token=access_token,
            refresh_token=refresh_token
        )

    def _validate_input(self, input_data: SignUpInput) -> None:
        """验证输入数据"""
        if not input_data.display_name or not input_data.display_name.strip():
            raise ValueError("Display name is required")
        
        if len(input_data.display_name.strip()) < 2:
            raise ValueError("Display name must be at least 2 characters")
        
        if len(input_data.display_name.strip()) > 50:
            raise ValueError("Display name must be less than 50 characters")
        
        if not input_data.email or not input_data.email.strip():
            raise ValueError("Email is required")
        
        if not self._is_valid_email(input_data.email):
            raise ValueError("Invalid email format")
        
        if not input_data.password:
            raise ValueError("Password is required")

    def _check_user_exists(self, email: str, display_name: str) -> None:
        """检查用户是否已存在"""
        existing_user_by_email = self._user_repo.find_by_email(email)
        if existing_user_by_email:
            raise ValueError("User with this email already exists")
        
        existing_user_by_name = self._user_repo.find_by_display_name(display_name)
        if existing_user_by_name:
            raise ValueError("User with this display name already exists")

    def _validate_password_strength(self, password: str) -> None:
        """验证密码强度"""
        validation_result = self._password_hasher.validate_password_strength(password)
        
        if not validation_result.get("is_strong", False):
            error_messages = []
            
            if not validation_result.get("min_length", False):
                error_messages.append("Password must be at least 8 characters long")
            
            if not validation_result.get("has_lowercase", False):
                error_messages.append("Password must contain at least one lowercase letter")
            
            if not validation_result.get("has_uppercase", False):
                error_messages.append("Password must contain at least one uppercase letter")
            
            if not validation_result.get("has_digit", False):
                error_messages.append("Password must contain at least one digit")
            
            if not validation_result.get("has_special", False):
                error_messages.append("Password must contain at least one special character")
            
            if not validation_result.get("no_common_patterns", False):
                error_messages.append("Password contains common patterns and is too weak")
            
            raise ValueError(f"Password does not meet requirements: {'; '.join(error_messages)}")

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email.strip()) is not None
