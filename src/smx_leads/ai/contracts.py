from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LeadAIClient(Protocol):
    """
    Host-provided AI client contract.

    smx-leads must not instantiate or own LLM models directly.
    The host SyntaxMatrix project provides an implementation of this protocol.
    """

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class LeadAIInsight:
    summary: str
    category: str
    priority: str
    suggested_status: str
    recommended_action: str
    draft_reply: str
    spam_risk: str
    model_name: str | None = None
    raw: dict[str, Any] | None = None
