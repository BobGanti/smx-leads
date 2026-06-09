from __future__ import annotations

from typing import Any

from smx_leads.ai.contracts import LeadAIClient, LeadAIInsight
from smx_leads.ai.prompts import build_lead_analysis_prompt
from smx_leads.repository import LeadSubmission


DEFAULT_INSIGHT = {
    "summary": "",
    "category": "general_enquiry",
    "priority": "medium",
    "suggested_status": "reviewed",
    "recommended_action": "",
    "draft_reply": "",
    "spam_risk": "low",
}


class LeadAIService:
    """
    Lead intelligence workflow.

    This service never creates or owns AI models.
    It only uses a host-provided LeadAIClient.
    """

    def __init__(self, *, ai_client: LeadAIClient | None = None):
        self.ai_client = ai_client

    def is_enabled(self) -> bool:
        return self.ai_client is not None

    def analyze_lead(self, lead: LeadSubmission) -> LeadAIInsight:
        if self.ai_client is None:
            raise RuntimeError(
                "Lead AI client is not configured. "
                "The host SyntaxMatrix project must provide the AI client."
            )

        prompt = build_lead_analysis_prompt(lead)
        raw = self.ai_client.generate_lead_insight(prompt=prompt)

        return normalize_lead_ai_response(raw)


def normalize_lead_ai_response(raw: dict[str, Any] | None) -> LeadAIInsight:
    data = dict(DEFAULT_INSIGHT)

    if raw:
        data.update(
            {
                key: value
                for key, value in raw.items()
                if value is not None
            }
        )

    return LeadAIInsight(
        summary=str(data.get("summary") or ""),
        category=_safe_choice(
            data.get("category"),
            allowed={
                "general_enquiry",
                "demo_request",
                "pilot_request",
                "support_request",
                "partnership",
                "waitlist",
                "sales",
                "spam",
            },
            default="general_enquiry",
        ),
        priority=_safe_choice(
            data.get("priority"),
            allowed={"low", "medium", "high"},
            default="medium",
        ),
        suggested_status=_safe_choice(
            data.get("suggested_status"),
            allowed={"new", "reviewed", "contacted", "closed", "spam"},
            default="reviewed",
        ),
        recommended_action=str(data.get("recommended_action") or ""),
        draft_reply=str(data.get("draft_reply") or ""),
        spam_risk=_safe_choice(
            data.get("spam_risk"),
            allowed={"low", "medium", "high"},
            default="low",
        ),
        model_name=(
            str(data.get("model_name"))
            if data.get("model_name") is not None
            else None
        ),
        raw=raw or {},
    )


def _safe_choice(value: Any, *, allowed: set[str], default: str) -> str:
    normalized = str(value or "").strip().lower()

    if normalized in allowed:
        return normalized

    return default
