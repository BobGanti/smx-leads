import json

import pytest

from smx_leads.ai.profiles import build_lead_ai_client_from_profile


class FakeLegacyLeadClient:
    def __init__(self):
        self.prompts = []

    def generate_lead_insight(self, *, prompt: str):
        self.prompts.append(prompt)
        return {
            "summary": "Legacy-compatible insight.",
            "category": "demo_request",
        }


class FakeOpenAICompatibleClient:
    def __init__(self):
        self.chat = self
        self.completions = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type(
            "Message",
            (),
            {
                "content": json.dumps(
                    {
                        "summary": "OpenAI-compatible insight.",
                        "category": "sales",
                        "priority": "high",
                    }
                )
            },
        )()
        choice = type("Choice", (), {"message": message})()
        usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        )()
        return type("Response", (), {"choices": [choice], "usage": usage})()


def test_build_lead_ai_client_accepts_legacy_host_client():
    legacy = FakeLegacyLeadClient()

    client = build_lead_ai_client_from_profile(legacy)

    result = client.generate_lead_insight(prompt="Analyze this lead.")

    assert result["summary"] == "Legacy-compatible insight."
    assert legacy.prompts == ["Analyze this lead."]


def test_build_lead_ai_client_accepts_single_provider_profile():
    provider_client = FakeOpenAICompatibleClient()

    client = build_lead_ai_client_from_profile(
        {
            "provider": "xai",
            "model": "grok-test",
            "api_key": "not-used-by-package",
            "client": provider_client,
        }
    )

    result = client.generate_lead_insight(prompt="Analyze this lead.")

    assert result["summary"] == "OpenAI-compatible insight."
    assert result["category"] == "sales"
    assert result["model_name"] == "grok-test"
    assert result["usage"]["provider"] == "xai"
    assert result["usage"]["model"] == "grok-test"
    assert result["usage"]["input_tokens"] == 11
    assert result["usage"]["output_tokens"] == 7
    assert result["usage"]["thinking_tokens"] == 0
    assert result["usage"]["other_tokens"] == 0
    assert result["usage"]["total_tokens"] == 18
    assert provider_client.calls[0]["model"] == "grok-test"
    assert provider_client.calls[0]["response_format"] == {"type": "json_object"}
    assert "Agent name: leads_final_insight" in provider_client.calls[0]["messages"][-1]["content"]


def test_build_lead_ai_client_accepts_labeled_main_assistant_profile():
    main_client = FakeOpenAICompatibleClient()
    assistant_client = FakeOpenAICompatibleClient()

    client = build_lead_ai_client_from_profile(
        {
            "main": {
                "provider": "xai",
                "model": "grok-main",
                "client": main_client,
            },
            "assistant": {
                "provider": "alibaba",
                "model": "qwen-assistant",
                "client": assistant_client,
            },
        }
    )

    result = client.generate_lead_insight(prompt="Analyze this lead.")

    assert result["summary"] == "OpenAI-compatible insight."
    assert assistant_client.calls[0]["model"] == "qwen-assistant"
    assert main_client.calls[0]["model"] == "grok-main"
    assert "assistant_context" in main_client.calls[0]["messages"][-1]["content"]
    assert result["usage"]["provider"] == "combined"
    assert result["usage"]["model"] == "main+assistant"
    assert result["usage"]["input_tokens"] == 22
    assert result["usage"]["output_tokens"] == 14
    assert result["usage"]["total_tokens"] == 36
    assert result["usage_by_profile"]["main"]["model"] == "grok-main"
    assert result["usage_by_profile"]["assistant"]["model"] == "qwen-assistant"
    assert result["usage_by_profile"]["assistant"]["provider"] == "alibaba"


def test_labeled_profile_does_not_require_assistant_none():
    main_client = FakeOpenAICompatibleClient()

    client = build_lead_ai_client_from_profile(
        {
            "main": {
                "provider": "xai",
                "model": "grok-main",
                "client": main_client,
            },
        }
    )

    result = client.generate_lead_insight(prompt="Analyze this lead.")

    assert result["summary"] == "OpenAI-compatible insight."
    assert main_client.calls[0]["model"] == "grok-main"


def test_unsupported_provider_is_rejected():
    with pytest.raises(ValueError, match="Unsupported leads AI provider"):
        build_lead_ai_client_from_profile(
            {
                "provider": "grok",
                "model": "wrong-provider-name",
                "client": object(),
            }
        )
