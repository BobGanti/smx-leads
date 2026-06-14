from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LeadAIClientError(ValueError):
    pass


@dataclass(frozen=True)
class LeadAIUsage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    thinking_tokens: int = 0
    other_tokens: int = 0
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "thinking_tokens": self.thinking_tokens,
            "other_tokens": self.other_tokens,
            "total_tokens": self.total_tokens,
            "raw": self.raw or {},
        }


@dataclass(frozen=True)
class LeadAIResult:
    data: dict[str, Any]
    usage: LeadAIUsage


class LeadAIClient(Protocol):
    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        ...


class LeadAIAgentClient(Protocol):
    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
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
