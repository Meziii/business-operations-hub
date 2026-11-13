import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TeamOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str


class TeamWithCount(TeamOut):
    member_count: int


class TeamCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=100)


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    teams: list[TeamOut]


class MeOut(UserOut):
    organization_name: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    role: Role
    password: str = Field(min_length=12, max_length=128)
    team_ids: list[uuid.UUID] = []


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    team_ids: list[uuid.UUID] | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuditOut(ORMModel):
    id: int
    action: str
    entity: str
    entity_id: str | None
    actor_email: str | None
    details: dict[str, Any]
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    database: str
    ai_provider: str
