"""SQLAlchemy ORM models for ContentForge."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class SourceType(str, enum.Enum):
    text = "text"
    pdf = "pdf"
    docx = "docx"
    url = "url"
    image = "image"


class OutputType(str, enum.Enum):
    linkedin_post = "linkedin_post"
    twitter = "twitter"
    advisory = "advisory"
    executive_summary = "executive_summary"
    presentation = "presentation"
    video_package = "video_package"
    infographic = "infographic"


# ── Tables ───────────────────────────────────────────────────────────────────

class User(Base):
    """Platform user (admin or operator)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.operator, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Job(Base):
    """A content generation job submitted by an operator."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of raw input
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="jobs")
    outputs: Mapped[list["GeneratedOutput"]] = relationship("GeneratedOutput", back_populates="job")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="job")


class GeneratedOutput(Base):
    """One generated deliverable (e.g. LinkedIn post) for a job."""

    __tablename__ = "generated_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    output_type: Mapped[OutputType] = mapped_column(Enum(OutputType), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)  # validated Pydantic dict
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of content JSON
    grounding_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="outputs")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="output")


class AuditLog(Base):
    """Immutable audit record for every generation event."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    output_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("generated_outputs.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
    job: Mapped["Job | None"] = relationship("Job", back_populates="audit_logs")
    output: Mapped["GeneratedOutput | None"] = relationship("GeneratedOutput", back_populates="audit_logs")


class PromptTemplate(Base):
    """Editable LLM prompt templates, one per output type (admin-managed)."""

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    output_type: Mapped[OutputType] = mapped_column(Enum(OutputType), unique=True, nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
