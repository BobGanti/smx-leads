from __future__ import annotations

import json
from typing import Any

from smx_leads.ai.contracts import LeadAIClient


SUPPORTED_PROVIDERS = {
    "google",
    "openai",
    "anthropic",
    "xai",
    "alibaba",
    "deepseek",
    "moonshotai",
}

OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
    "xai",
    "alibaba",
    "deepseek",
    "moonshotai",
}


class LeadAIProfileClient:
    """
    Lead AI client built from a host-provided AI profile.

    The host owns provider selection, model selection, API key retrieval,
    and provider client construction. smx-leads owns this adapter and the
    lead intelligence workflow.
    """

    def __init__(self, *, profile: dict[str, Any]):
        self.profile = profile
        self.provider = str(profile.get("provider") or "").strip().lower()
        self.model = str(profile.get("model") or "").strip()
        self.client = profile.get("client")

        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported leads AI provider: {self.provider}")

        if not self.model:
            raise ValueError("leads ai_profile must include a model")

        if self.client is None:
            raise ValueError("leads ai_profile must include a provider client")

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        if hasattr(self.client, "generate_lead_insight"):
            return dict(self.client.generate_lead_insight(prompt=prompt))

        if self.provider == "google":
            return _parse_response_text(_call_google(self.client, model=self.model, prompt=prompt))

        if self.provider == "openai":
            return _parse_response_text(_call_openai_responses(self.client, model=self.model, prompt=prompt))

        if self.provider == "anthropic":
            return _parse_response_text(_call_anthropic_messages(self.client, model=self.model, prompt=prompt))

        if self.provider in OPENAI_COMPATIBLE_CHAT_PROVIDERS:
            return _parse_response_text(_call_openai_compatible_chat(self.client, model=self.model, prompt=prompt))

        raise ValueError(f"unsupported leads AI provider: {self.provider}")


class LeadAIRoutingClient:
    """
    Routing wrapper for labeled ai_profile dictionaries.

    Current smx-leads has one lead insight workflow, so it uses the main
    profile. The assistant profile is accepted and retained for future
    narrower lead-analysis agents without changing the public host contract.
    """

    def __init__(
        self,
        *,
        main_client: LeadAIClient,
        assistant_client: LeadAIClient | None = None,
    ):
        self.main_client = main_client
        self.assistant_client = assistant_client

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        return self.main_client.generate_lead_insight(prompt=prompt)


def build_lead_ai_client_from_profile(profile: Any) -> LeadAIClient | None:
    if profile is None:
        return None

    if _is_labeled_ai_profile(profile):
        main_profile = profile.get("main")
        assistant_profile = profile.get("assistant")

        if main_profile is None:
            raise ValueError("leads labeled ai_profile must include 'main'")

        main_client = build_lead_ai_client_from_profile(main_profile)
        assistant_client = (
            build_lead_ai_client_from_profile(assistant_profile)
            if assistant_profile is not None
            else None
        )

        if main_client is None:
            raise ValueError("leads labeled ai_profile main profile is not configured")

        return LeadAIRoutingClient(
            main_client=main_client,
            assistant_client=assistant_client,
        )

    if isinstance(profile, dict):
        return LeadAIProfileClient(profile=profile)

    if hasattr(profile, "generate_lead_insight"):
        return profile

    raise ValueError("leads ai_profile must be a provider profile or labeled profile")


def _is_labeled_ai_profile(profile: Any) -> bool:
    return isinstance(profile, dict) and (
        "main" in profile or "assistant" in profile
    )


def _call_google(client: Any, *, model: str, prompt: str) -> str:
    if hasattr(client, "models") and hasattr(client.models, "generate_content"):
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return _extract_text(response)

    if hasattr(client, "generate_content"):
        response = client.generate_content(
            model=model,
            contents=prompt,
        )
        return _extract_text(response)

    raise ValueError("google leads ai_profile client does not support content generation")


def _call_openai_responses(client: Any, *, model: str, prompt: str) -> str:
    response = client.responses.create(
        model=model,
        input=prompt,
    )

    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    return _extract_text(response)


def _call_anthropic_messages(client: Any, *, model: str, prompt: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=1200,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return _extract_text(response)


def _call_openai_compatible_chat(client: Any, *, model: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        response_format={"type": "json_object"},
    )

    return _extract_text(response)


def _extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response

    text = getattr(response, "text", None)
    if text:
        return str(text)

    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    choices = getattr(response, "choices", None)
    if choices:
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)

    content = getattr(response, "content", None)
    if isinstance(content, list):
        parts = []
        for item in content:
            item_text = getattr(item, "text", None)
            if item_text:
                parts.append(str(item_text))
        if parts:
            return "\n".join(parts)

    if isinstance(response, dict):
        for key in ("text", "output_text", "content"):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value

    return str(response)


def _parse_response_text(text: str) -> dict[str, Any]:
    value = text.strip()

    if value.startswith("```"):
        value = value.strip("`").strip()
        if value.lower().startswith("json"):
            value = value[4:].strip()

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {"summary": value}

    if not isinstance(parsed, dict):
        return {"summary": value}

    return parsed
