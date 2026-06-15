from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select

from smx_leads.ai.contracts import LeadAIInsight
from smx_leads.models import LeadAIInsightRow


@dataclass(frozen=True)
class StoredLeadAIInsight:
    id: int
    lead_public_id: str

    summary: str
    category: str
    priority: str
    suggested_status: str
    recommended_action: str
    draft_reply: str
    spam_risk: str
    model_name: str | None
    raw: dict[str, Any]

    created_at: datetime | None = None


class LeadAIInsightRepository:
    def __init__(self, session):
        self.session = session

    def create_insight(
        self,
        *,
        lead_public_id: str,
        insight: LeadAIInsight,
    ) -> StoredLeadAIInsight:
        lead_public_id = (lead_public_id or "").strip()

        if not lead_public_id:
            raise ValueError("lead_public_id is required.")

        row = LeadAIInsightRow(
            lead_public_id=lead_public_id,
            summary=insight.summary,
            category=insight.category,
            priority=insight.priority,
            suggested_status=insight.suggested_status,
            recommended_action=insight.recommended_action,
            draft_reply=insight.draft_reply,
            spam_risk=insight.spam_risk,
            model_name=insight.model_name or "",
            raw=insight.raw or {},
        )

        self.session.add(row)
        self.session.flush()

        return _to_domain(row)

    def list_for_lead(
        self,
        *,
        lead_public_id: str,
        limit: int = 20,
    ) -> list[StoredLeadAIInsight]:
        statement = (
            select(LeadAIInsightRow)
            .where(LeadAIInsightRow.lead_public_id == lead_public_id)
            .order_by(LeadAIInsightRow.id.desc())
            .limit(limit)
        )

        rows = self.session.scalars(statement).all()

        return [_to_domain(row) for row in rows]

    def get_latest_for_lead(self, *, lead_public_id: str) -> StoredLeadAIInsight | None:
        items = self.list_for_lead(
            lead_public_id=lead_public_id,
            limit=1,
        )

        if not items:
            return None

        return items[0]

    def delete_for_lead(self, *, lead_public_id: str) -> int:
        rows = self.session.scalars(
            select(LeadAIInsightRow).where(
                LeadAIInsightRow.lead_public_id == lead_public_id
            )
        ).all()

        for row in rows:
            self.session.delete(row)

        self.session.flush()

        return len(rows)


def _to_domain(row: LeadAIInsightRow) -> StoredLeadAIInsight:
    return StoredLeadAIInsight(
        id=row.id,
        lead_public_id=row.lead_public_id,
        summary=row.summary,
        category=row.category,
        priority=row.priority,
        suggested_status=row.suggested_status,
        recommended_action=row.recommended_action,
        draft_reply=row.draft_reply,
        spam_risk=row.spam_risk,
        model_name=row.model_name or None,
        raw=dict(row.raw or {}),
        created_at=row.created_at,
    )
