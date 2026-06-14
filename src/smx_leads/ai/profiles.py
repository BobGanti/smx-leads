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
            data = dict(self.client.generate_lead_insight(prompt=prompt))
            data.setdefault("model_name", self.model)
            data.setdefault("usage", _empty_usage(provider=self.provider, model=self.model))
            return data

        if self.provider == "google":
            response = _call_google(self.client, model=self.model, prompt=prompt)
            return _parse_response(response, provider=self.provider, model=self.model)

        if self.provider == "openai":
            response = _call_openai_responses(self.client, model=self.model, prompt=prompt)
            return _parse_response(response, provider=self.provider, model=self.model)

        if self.provider == "anthropic":
            response = _call_anthropic_messages(self.client, model=self.model, prompt=prompt)
            return _parse_response(response, provider=self.provider, model=self.model)

        if self.provider in OPENAI_COMPATIBLE_CHAT_PROVIDERS:
            response = _call_openai_compatible_chat(self.client, model=self.model, prompt=prompt)
            return _parse_response(response, provider=self.provider, model=self.model)

        raise ValueError(f"unsupported leads AI provider: {self.provider}")


class LeadAIRoutingClient:
    """
    Routing wrapper for labeled ai_profile dictionaries.

    When an assistant profile is provided, smx-leads uses it for a narrow
    pre-analysis pass, then sends that context to the main profile for the
    final lead insight. Usage is accumulated across both profiles.
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
        if self.assistant_client is None:
            return self.main_client.generate_lead_insight(prompt=prompt)

        assistant_prompt = (
            "You are the assistant lead-analysis model. "
            "Extract concise supporting context for the main lead-analysis model. "
            "Return JSON with summary, category, priority, spam_risk, key_points, and recommended_focus.\n\n"
            f"{prompt}"
        )
        assistant_result = dict(self.assistant_client.generate_lead_insight(prompt=assistant_prompt))
        assistant_context = _assistant_context_from_result(assistant_result)

        main_prompt = (
            f"{prompt}\n\n"
            "Assistant pre-analysis context for support only:\n"
            f"{json.dumps(assistant_context, ensure_ascii=False)}\n\n"
            "Use the assistant context only if it is relevant and produce the final lead insight JSON."
        )
        main_result = dict(self.main_client.generate_lead_insight(prompt=main_prompt))

        main_usage = dict(main_result.get("usage", {}) or {})
        assistant_usage = dict(assistant_result.get("usage", {}) or {})
        main_result["usage_by_profile"] = {
            "main": main_usage,
            "assistant": assistant_usage,
        }
        main_result["usage"] = _combine_usage_profiles(
            main_usage=main_usage,
            assistant_usage=assistant_usage,
        )
        return main_result


def _assistant_context_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": result.get("summary", ""),
        "category": result.get("category", ""),
        "priority": result.get("priority", ""),
        "spam_risk": result.get("spam_risk", ""),
        "recommended_action": result.get("recommended_action", ""),
        "raw": result.get("raw", {}),
    }


def _combine_usage_profiles(
    *,
    main_usage: dict[str, Any],
    assistant_usage: dict[str, Any],
) -> dict[str, Any]:
    input_tokens = _coerce_int(main_usage.get("input_tokens")) + _coerce_int(assistant_usage.get("input_tokens"))
    output_tokens = _coerce_int(main_usage.get("output_tokens")) + _coerce_int(assistant_usage.get("output_tokens"))
    thinking_tokens = _coerce_int(main_usage.get("thinking_tokens")) + _coerce_int(assistant_usage.get("thinking_tokens"))
    other_tokens = _coerce_int(main_usage.get("other_tokens")) + _coerce_int(assistant_usage.get("other_tokens"))
    total_tokens = _coerce_int(main_usage.get("total_tokens")) + _coerce_int(assistant_usage.get("total_tokens"))

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens + thinking_tokens + other_tokens

    return {
        "provider": "combined",
        "model": "main+assistant",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "other_tokens": other_tokens,
        "total_tokens": total_tokens,
        "raw": {
            "main": main_usage,
            "assistant": assistant_usage,
        },
    }


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
        return response

    if hasattr(client, "generate_content"):
        response = client.generate_content(
            model=model,
            contents=prompt,
        )
        return response

    raise ValueError("google leads ai_profile client does not support content generation")


def _call_openai_responses(client: Any, *, model: str, prompt: str) -> str:
    response = client.responses.create(
        model=model,
        input=prompt,
    )

    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    return response


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

    return response


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

    return response


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


def _parse_response(response: Any, *, provider: str, model: str) -> dict[str, Any]:
    parsed = _parse_response_text(_extract_text(response))
    parsed.setdefault("model_name", model)
    parsed["usage"] = _extract_usage(response, provider=provider, model=model)
    return parsed


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


def _extract_usage(response: Any, *, provider: str, model: str) -> dict[str, Any]:
    if provider == "google":
        usage = getattr(response, "usage_metadata", None)
        input_tokens = _coerce_int(getattr(usage, "prompt_token_count", 0))
        output_tokens = _coerce_int(getattr(usage, "candidates_token_count", 0))
        thinking_tokens = _coerce_int(getattr(usage, "thoughts_token_count", 0))
        total_tokens = _coerce_int(getattr(usage, "total_token_count", 0))
        raw = {
            "prompt_token_count": input_tokens,
            "candidates_token_count": output_tokens,
            "thoughts_token_count": thinking_tokens,
            "total_token_count": total_tokens,
        }
    else:
        usage = getattr(response, "usage", None)
        input_tokens = _coerce_int(_get_usage_value(usage, "input_tokens"))
        output_tokens = _coerce_int(_get_usage_value(usage, "output_tokens"))
        thinking_tokens = _coerce_int(_get_usage_value(usage, "thinking_tokens"))
        total_tokens = _coerce_int(_get_usage_value(usage, "total_tokens"))
        raw = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        }

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens + thinking_tokens

    other_tokens = max(total_tokens - input_tokens - output_tokens - thinking_tokens, 0)

    return {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "other_tokens": other_tokens,
        "total_tokens": total_tokens,
        "raw": raw,
    }


def _empty_usage(*, provider: str, model: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "other_tokens": 0,
        "total_tokens": 0,
        "raw": {},
    }


def _get_usage_value(usage: Any, key: str) -> Any:
    if usage is None:
        return 0

    if isinstance(usage, dict):
        return usage.get(key, 0)

    return getattr(usage, key, 0)


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
