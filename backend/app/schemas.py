"""Pydantic 请求/响应模型。"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------- 认证 ----------------

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    auth_source: str = "local"
    role: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool = True
    must_change_password: bool = False


class TokenOut(BaseModel):
    token: Optional[str] = None
    user: Optional[UserOut] = None
    pending: bool = False
    message: Optional[str] = None


# ---------------- 管理员 ----------------

class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: Optional[str] = None
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: bool = True


class UserUpdateIn(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # 重置密码：设置后 must_change_password = true


class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)


class DepartmentUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class ConfigsUpdateIn(BaseModel):
    configs: Dict[str, str]


class ResetCaptchaIn(BaseModel):
    message_id: int


# ---------------- 匿名 ----------------

class AnonymousQueryIn(BaseModel):
    id: int
    captcha: str = Field(min_length=1, max_length=16)


class EvaluateIn(BaseModel):
    captcha: str = Field(min_length=1, max_length=16)
    satisfied: bool
    content: Optional[str] = Field(default=None, max_length=2000)


# ---------------- 秘书 ----------------

class SecretaryReviewIn(BaseModel):
    result: Literal["APPROVED", "REJECTED", "REFUSED"]
    comment: Optional[str] = Field(default=None, max_length=2000)


class TaskAssignItem(BaseModel):
    department_id: int
    title: str = Field(min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, max_length=5000)


class AssignTasksIn(BaseModel):
    tasks: List[TaskAssignItem] = Field(min_length=1, max_length=50)


class TaskReviewIn(BaseModel):
    result: Literal["APPROVED", "REJECTED"]
    comment: Optional[str] = Field(default=None, max_length=2000)


# ---------------- 院长 ----------------

class InstructionIn(BaseModel):
    instruction: str = Field(min_length=1, max_length=5000)


class PrincipalRejectIn(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)
