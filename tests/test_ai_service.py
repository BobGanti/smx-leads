import pytest

from smx_leads.ai import LeadAIService, build_lead_analysis_prompt
from smx_leads.models import LeadSubmissionStatus
from smx_leads.repository import LeadSubmission


class FakeLeadAIClient:
    def __init__(self):
        self.prompts = []

    def generate_lead_insight(self, *, prompt: str):
        self.prompts.append(prompt)
        return {
            "summary": "Bob wants a demo for a SyntaxMatrix AI product.",
            "category": "demo_request",
            "priority": "high",
            "suggested_status": "reviewed",
            "recommended_action": "Offer demo slots within 24 hours.",
            "draft_reply": "Hi Bob, thanks for your interest. We can arrange a demo this week.",
            "spam_risk": "low",
            "model_name": "host-provided-model",
        }


def make_lead():
    return LeadSubmission(
        public_id="lead_test123",
        source="demo",
        status=LeadSubmissionStatus.NEW.value,
        full_name="Bob Nti",
        email="bob@example.com",
        phone="123",
        company="SyntaxMatrix",
        subject="Demo request",
        message="I want a demo of your AI platform.",
        internal_notes="",
        extra={},
    )


def test_prompt_contains_lead_context():
    prompt = build_lead_analysis_prompt(make_lead())

    assert "Lead Intelligence Agent" in prompt
    assert "lead_test123" in prompt
    assert "Bob Nti" in prompt
    assert "bob@example.com" in prompt
    assert "I want a demo of your AI platform." in prompt
    assert "Return only structured JSON-compatible data" in prompt


def test_ai_service_requires_host_provided_client():
    service = LeadAIService(ai_client=None)

    assert service.is_enabled() is False

    with pytest.raises(RuntimeError, match="host SyntaxMatrix project"):
        service.analyze_lead(make_lead())


def test_ai_service_analyzes_lead_with_host_client():
    client = FakeLeadAIClient()
    service = LeadAIService(ai_client=client)

    insight = service.analyze_lead(make_lead())

    assert service.is_enabled() is True
    assert len(client.prompts) == 1

    assert insight.summary == "Bob wants a demo for a SyntaxMatrix AI product."
    assert insight.category == "demo_request"
    assert insight.priority == "high"
    assert insight.suggested_status == "reviewed"
    assert insight.recommended_action == "Offer demo slots within 24 hours."
    assert insight.draft_reply.startswith("Hi Bob")
    assert insight.spam_risk == "low"
    assert insight.model_name == "host-provided-model"


def test_ai_service_normalizes_untrusted_ai_values():
    class BadAIClient:
        def generate_lead_insight(self, *, prompt: str):
            return {
                "summary": "Suspicious enquiry.",
                "category": "unknown-category",
                "priority": "urgent",
                "suggested_status": "paid",
                "recommended_action": "Review manually.",
                "draft_reply": "",
                "spam_risk": "extreme",
            }

    service = LeadAIService(ai_client=BadAIClient())
    insight = service.analyze_lead(make_lead())

    assert insight.summary == "Suspicious enquiry."
    assert insight.category == "general_enquiry"
    assert insight.priority == "medium"
    assert insight.suggested_status == "reviewed"
    assert insight.spam_risk == "low"
    assert insight.recommended_action == "Review manually."
