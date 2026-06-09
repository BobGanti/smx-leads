from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class LeadsBase(DeclarativeBase):
    pass


class LeadSubmissionStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    CLOSED = "closed"
    SPAM = "spam"


class LeadSubmissionRow(LeadsBase):
    __tablename__ = "smx_lead_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: f"lead_{uuid.uuid4().hex[:18]}",
    )

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="contact")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=LeadSubmissionStatus.NEW.value)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    internal_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LeadAIInsightRow(LeadsBase):
    __tablename__ = "smx_lead_ai_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    lead_public_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("smx_lead_submissions.public_id"),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general_enquiry")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    suggested_status: Mapped[str] = mapped_column(String(32), nullable=False, default="reviewed")
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    draft_reply: Mapped[str] = mapped_column(Text, nullable=False, default="")
    spam_risk: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

