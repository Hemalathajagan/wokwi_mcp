"""SQLAlchemy models and Pydantic schemas."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy model
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_type: Mapped[str] = mapped_column(String(50), default="wokwi")
    wokwi_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fault_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GoogleAuthRequest(BaseModel):
    token: str  # Google ID token from the frontend


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class SignupRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    id: int
    project_type: str = "wokwi"
    wokwi_url: str | None = None
    project_id: str | None = None
    source_path: str | None = None
    project_name: str | None = None
    summary_json: str | None = None
    report_json: str | None = None
    fault_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
