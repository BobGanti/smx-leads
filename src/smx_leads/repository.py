from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select

from smx_leads.models import LeadSubmissionRow, LeadSubmissionStatus


@dataclass(frozen=True)
class LeadSubmission:
    public_id: str
    source: str
    status: str

    full_name: str
    email: str
    phone: str
    company: str

    subject: str
    message: str

    internal_notes: str
    extra: dict[str, Any] = field(default_factory=dict)

    created_at: datetime | None = None
    updated_at: datetime | None = None


class LeadRepository:
    def __init__(self, session):
        self.session = session

    def create_submission(
        self,
        *,
        full_name: str,
        email: str,
        message: str,
        source: str = "contact",
        phone: str = "",
        company: str = "",
        subject: str = "",
        extra: dict[str, Any] | None = None,
    ) -> LeadSubmission:
        full_name = (full_name or "").strip()
        email = (email or "").strip().lower()
        message = (message or "").strip()
        source = (source or "contact").strip().lower()
        phone = (phone or "").strip()
        company = (company or "").strip()
        subject = (subject or "").strip()

        if not full_name:
            raise ValueError("Full name is required.")

        if not email:
            raise ValueError("Email is required.")

        if "@" not in email:
            raise ValueError("A valid email is required.")

        if not message:
            raise ValueError("Message is required.")

        row = LeadSubmissionRow(
            source=source,
            status=LeadSubmissionStatus.NEW.value,
            full_name=full_name,
            email=email,
            phone=phone,
            company=company,
            subject=subject,
            message=message,
            extra=extra or {},
        )

        self.session.add(row)
        self.session.flush()

        return _to_domain(row)

    def list_submissions(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[LeadSubmission]:
        statement = select(LeadSubmissionRow).order_by(LeadSubmissionRow.created_at.desc())

        if status:
            statement = statement.where(LeadSubmissionRow.status == status)

        if source:
            statement = statement.where(LeadSubmissionRow.source == source)

        statement = statement.limit(limit)

        rows = self.session.scalars(statement).all()

        return [_to_domain(row) for row in rows]

    def get_submission(self, public_id: str) -> LeadSubmission | None:
        row = self._get_row(public_id)

        if row is None:
            return None

        return _to_domain(row)

    def update_status(
        self,
        *,
        public_id: str,
        status: str,
        internal_notes: str | None = None,
    ) -> LeadSubmission:
        normalized_status = (status or "").strip().lower()

        allowed = {item.value for item in LeadSubmissionStatus}
        if normalized_status not in allowed:
            raise ValueError(f"Invalid lead status: {status}")

        row = self._get_row(public_id)

        if row is None:
            raise ValueError(f"Lead submission not found: {public_id}")

        row.status = normalized_status

        if internal_notes is not None:
            row.internal_notes = internal_notes.strip()

        self.session.flush()

        return _to_domain(row)

    def delete_submission(self, *, public_id: str) -> bool:
        row = self._get_row(public_id)

        if row is None:
            return False

        self.session.delete(row)
        self.session.flush()

        return True

    def _get_row(self, public_id: str) -> LeadSubmissionRow | None:
        statement = select(LeadSubmissionRow).where(
            LeadSubmissionRow.public_id == public_id
        )

        return self.session.scalars(statement).first()


def _to_domain(row: LeadSubmissionRow) -> LeadSubmission:
    return LeadSubmission(
        public_id=row.public_id,
        source=row.source,
        status=row.status,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        company=row.company,
        subject=row.subject,
        message=row.message,
        internal_notes=row.internal_notes,
        extra=dict(row.extra or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
