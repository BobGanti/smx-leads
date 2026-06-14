from __future__ import annotations

import json
import re
from typing import Any

from smx_leads.ai.contracts import LeadAIClientError, LeadAIResult, LeadAIUsage


OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
    "xai",
    "alibaba",
    "deepseek",
    "moonshotai",
}

LEAD_ASSISTANT_AGENT_NAME = "leads_assistant_context"
LEAD_MAIN_AGENT_NAME = "leads_final_insight"


class HostLeadAIClientAdapter:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        client: Any,
    ):
        if not provider:
            raise LeadAIClientError("Host AI profile requires a provider.")
        if not model:
            raise LeadAIClientError("Host AI profile requires a model.")
        if client is None:
            raise LeadAIClientError("Host AI profile requires a client.")

        self.provider = provider
        self.model = model
        self.client = client

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        data = dict(self.client.generate_lead_insight(prompt=prompt))
        data.setdefault("model_name", self.model)
        data.setdefault("usage", _empty_usage(provider=self.provider, model=self.model).to_dict())
        return data

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        prompt = _build_agent_prompt(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )
        data = self.generate_lead_insight(prompt=prompt)
        usage = _usage_from_dict(
            data.get("usage"),
            fallback_provider=self.provider,
            fallback_model=self.model,
        )
        return LeadAIResult(data=data, usage=usage)


class _BaseLeadAIAgentClient:
    provider: str
    model: str

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        result = self.run_agent_task(
            agent_name=LEAD_MAIN_AGENT_NAME,
            system_prompt=_lead_main_system_prompt(),
            task_prompt=prompt,
            expected_schema=_lead_insight_schema(),
            context={},
        )
        data = dict(result.data)
        data.setdefault("model_name", result.usage.model)
        data["usage"] = result.usage.to_dict()
        return data


class GoogleLeadAIClient(_BaseLeadAIAgentClient):
    def __init__(
        self,
        *,
        model: str,
        client: Any,
    ):
        if not model:
            raise LeadAIClientError("Google AI profile requires a model.")
        if client is None:
            raise LeadAIClientError("Google AI profile requires a client.")

        self.provider = "google"
        self.model = model
        self.client = client

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        prompt = _build_agent_prompt(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )

        response_text, usage = self._generate_text(prompt)
        return LeadAIResult(
            data=_parse_json_object(response_text, agent_name=agent_name),
            usage=usage,
        )

    def _generate_text(self, prompt: str) -> tuple[str, LeadAIUsage]:
        try:
            if hasattr(self.client, "models") and hasattr(self.client.models, "generate_content"):
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
            elif hasattr(self.client, "generate_content"):
                response = self.client.generate_content(
                    model=self.model,
                    contents=prompt,
                )
            else:
                raise LeadAIClientError("Google AI profile client does not support content generation.")
        except TypeError:
            if hasattr(self.client, "models") and hasattr(self.client.models, "generate_content"):
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
            else:
                response = self.client.generate_content(
                    model=self.model,
                    contents=prompt,
                )
        except Exception as exc:
            raise LeadAIClientError(f"Google AI request failed: {exc}") from exc

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text, _extract_google_usage(response, provider=self.provider, model=self.model)

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            for part in parts or []:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text, _extract_google_usage(response, provider=self.provider, model=self.model)

        raise LeadAIClientError("Google AI response did not contain text.")


class OpenAIResponsesLeadAIClient(_BaseLeadAIAgentClient):
    def __init__(
        self,
        *,
        model: str,
        client: Any,
    ):
        if not model:
            raise LeadAIClientError("OpenAI AI profile requires a model.")
        if client is None:
            raise LeadAIClientError("OpenAI AI profile requires a client.")

        self.provider = "openai"
        self.model = model
        self.client = client

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        prompt = _build_agent_prompt(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )

        response_text, usage = self._generate_text(prompt)
        return LeadAIResult(
            data=_parse_json_object(response_text, agent_name=agent_name),
            usage=usage,
        )

    def _generate_text(self, prompt: str) -> tuple[str, LeadAIUsage]:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": {"type": "json_object"}},
            )
        except TypeError:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
        except Exception as exc:
            raise LeadAIClientError(f"OpenAI Responses API request failed: {exc}") from exc

        text = getattr(response, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text, _extract_openai_usage(response, provider=self.provider, model=self.model)

        output = getattr(response, "output", None) or []
        for item in output:
            content = getattr(item, "content", None) or []
            for content_item in content:
                content_text = getattr(content_item, "text", None)
                if isinstance(content_text, str) and content_text.strip():
                    return content_text, _extract_openai_usage(response, provider=self.provider, model=self.model)

        raise LeadAIClientError("OpenAI Responses API response did not contain output text.")


class AnthropicLeadAIClient(_BaseLeadAIAgentClient):
    def __init__(
        self,
        *,
        model: str,
        client: Any,
        max_tokens: int = 2048,
    ):
        if not model:
            raise LeadAIClientError("Anthropic AI profile requires a model.")
        if client is None:
            raise LeadAIClientError("Anthropic AI profile requires a client.")

        self.provider = "anthropic"
        self.model = model
        self.client = client
        self.max_tokens = max_tokens

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        prompt = _build_agent_prompt(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )

        response_text, usage = self._generate_text(prompt)
        return LeadAIResult(
            data=_parse_json_object(response_text, agent_name=agent_name),
            usage=usage,
        )

    def _generate_text(self, prompt: str) -> tuple[str, LeadAIUsage]:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LeadAIClientError(f"Anthropic AI request failed: {exc}") from exc

        content = getattr(response, "content", None) or []
        for block in content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str) and block_text.strip():
                return block_text, _extract_anthropic_usage(response, provider=self.provider, model=self.model)

            if isinstance(block, dict):
                block_text = block.get("text")
                if isinstance(block_text, str) and block_text.strip():
                    return block_text, _extract_anthropic_usage(response, provider=self.provider, model=self.model)

        raise LeadAIClientError("Anthropic AI response did not contain text.")


class OpenAICompatibleChatLeadAIClient(_BaseLeadAIAgentClient):
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        client: Any,
        max_tokens: int = 2048,
        json_response_format: bool = True,
    ):
        if not provider:
            raise LeadAIClientError("OpenAI-compatible AI profile requires a provider.")
        if not model:
            raise LeadAIClientError("OpenAI-compatible AI profile requires a model.")
        if client is None:
            raise LeadAIClientError("OpenAI-compatible AI profile requires a client.")

        self.provider = provider
        self.model = model
        self.client = client
        self.max_tokens = max_tokens
        self.json_response_format = json_response_format

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        prompt = _build_agent_prompt(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )

        response_text, usage = self._generate_text(prompt)
        return LeadAIResult(
            data=_parse_json_object(response_text, agent_name=agent_name),
            usage=usage,
        )

    def _generate_text(self, prompt: str) -> tuple[str, LeadAIUsage]:
        request_kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
        }

        if self.json_response_format:
            request_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**request_kwargs)
        except TypeError:
            request_kwargs.pop("response_format", None)
            try:
                response = self.client.chat.completions.create(**request_kwargs)
            except TypeError:
                request_kwargs.pop("max_tokens", None)
                response = self.client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            raise LeadAIClientError(
                f"OpenAI-compatible Chat Completions request failed for provider {self.provider}: {exc}"
            ) from exc

        choices = getattr(response, "choices", None) or []
        for choice in choices:
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None) if message is not None else None

            if isinstance(content, str) and content.strip():
                return content, _extract_openai_compatible_chat_usage(
                    response,
                    provider=self.provider,
                    model=self.model,
                )

            if isinstance(choice, dict):
                message = choice.get("message") or {}
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content, _extract_openai_compatible_chat_usage(
                        response,
                        provider=self.provider,
                        model=self.model,
                    )

        raise LeadAIClientError(
            f"OpenAI-compatible Chat Completions response did not contain message content for provider {self.provider}."
        )


class LeadAIRoutingClient:
    def __init__(
        self,
        *,
        main_client: Any,
        assistant_client: Any | None = None,
    ):
        if main_client is None:
            raise LeadAIClientError("Leads AI routing requires a main client.")

        self.main_client = main_client
        self.assistant_client = assistant_client

    def generate_lead_insight(self, *, prompt: str) -> dict[str, Any]:
        if self.assistant_client is None:
            return self.main_client.generate_lead_insight(prompt=prompt)

        assistant_result = self.assistant_client.run_agent_task(
            agent_name=LEAD_ASSISTANT_AGENT_NAME,
            system_prompt=_lead_assistant_system_prompt(),
            task_prompt=prompt,
            expected_schema=_lead_assistant_schema(),
            context={},
        )

        main_result = self.main_client.run_agent_task(
            agent_name=LEAD_MAIN_AGENT_NAME,
            system_prompt=_lead_main_system_prompt(),
            task_prompt=prompt,
            expected_schema=_lead_insight_schema(),
            context={"assistant_context": assistant_result.data},
        )

        combined_usage = _combine_usage_profiles(
            main_usage=main_result.usage,
            assistant_usage=assistant_result.usage,
        )

        data = dict(main_result.data)
        data.setdefault("model_name", main_result.usage.model)
        data["usage"] = combined_usage.to_dict()
        data["usage_by_profile"] = {
            "main": main_result.usage.to_dict(),
            "assistant": assistant_result.usage.to_dict(),
        }
        return data

    def run_agent_task(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        task_prompt: str,
        expected_schema: dict[str, Any],
        context: dict[str, Any],
    ) -> LeadAIResult:
        return self.main_client.run_agent_task(
            agent_name=agent_name,
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            expected_schema=expected_schema,
            context=context,
        )


def build_lead_ai_client_from_profile(profile: Any):
    if not profile:
        return None

    if _is_labeled_ai_profile(profile):
        main_profile = profile.get("main")
        if not main_profile:
            raise LeadAIClientError("Labeled leads AI profile requires a main profile.")

        main_client = build_lead_ai_client_from_profile(main_profile)
        if main_client is None:
            raise LeadAIClientError("Labeled leads AI profile main profile did not create a client.")

        assistant_profile = profile.get("assistant")
        assistant_client = (
            build_lead_ai_client_from_profile(assistant_profile)
            if assistant_profile
            else None
        )

        return LeadAIRoutingClient(
            main_client=main_client,
            assistant_client=assistant_client,
        )

    if not isinstance(profile, dict):
        if hasattr(profile, "generate_lead_insight"):
            return profile
        raise LeadAIClientError("leads ai_profile must be a provider profile or labeled profile")

    provider = str(profile.get("provider", "")).strip().lower()
    model = str(profile.get("model", "")).strip()
    client = profile.get("client")

    if hasattr(client, "generate_lead_insight"):
        return HostLeadAIClientAdapter(
            provider=provider,
            model=model,
            client=client,
        )

    if provider == "google":
        return GoogleLeadAIClient(
            model=model,
            client=client,
        )

    if provider == "openai":
        return OpenAIResponsesLeadAIClient(
            model=model,
            client=client,
        )

    if provider == "anthropic":
        return AnthropicLeadAIClient(
            model=model,
            client=client,
            max_tokens=_coerce_int(profile.get("max_tokens", 2048)) or 2048,
        )

    if provider in OPENAI_COMPATIBLE_CHAT_PROVIDERS:
        return OpenAICompatibleChatLeadAIClient(
            provider=provider,
            model=model,
            client=client,
            max_tokens=_coerce_int(profile.get("max_tokens", 2048)) or 2048,
            json_response_format=bool(profile.get("json_response_format", True)),
        )

    raise LeadAIClientError(f"Unsupported leads AI provider: {provider or '<missing>'}")


def _is_labeled_ai_profile(profile: Any) -> bool:
    return isinstance(profile, dict) and (
        "main" in profile or "assistant" in profile
    )


def _extract_google_usage(response: Any, *, provider: str, model: str) -> LeadAIUsage:
    usage = getattr(response, "usage_metadata", None)

    input_tokens = _coerce_int(getattr(usage, "prompt_token_count", 0))
    output_tokens = _coerce_int(getattr(usage, "candidates_token_count", 0))
    thinking_tokens = _coerce_int(getattr(usage, "thoughts_token_count", 0))
    total_tokens = _coerce_int(getattr(usage, "total_token_count", 0))

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens + thinking_tokens

    other_tokens = max(total_tokens - input_tokens - output_tokens - thinking_tokens, 0)

    return LeadAIUsage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        other_tokens=other_tokens,
        total_tokens=total_tokens,
        raw={
            "prompt_token_count": input_tokens,
            "candidates_token_count": output_tokens,
            "thoughts_token_count": thinking_tokens,
            "total_token_count": total_tokens,
        },
    )


def _extract_openai_usage(response: Any, *, provider: str, model: str) -> LeadAIUsage:
    usage = getattr(response, "usage", None)

    input_tokens = _coerce_int(_get_usage_value(usage, "input_tokens"))
    output_tokens = _coerce_int(_get_usage_value(usage, "output_tokens"))
    thinking_tokens = _coerce_int(_get_usage_value(usage, "output_tokens_details.reasoning_tokens"))
    total_tokens = _coerce_int(_get_usage_value(usage, "total_tokens"))

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens

    other_tokens = max(total_tokens - input_tokens - output_tokens, 0)

    return LeadAIUsage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        other_tokens=other_tokens,
        total_tokens=total_tokens,
        raw={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        },
    )


def _extract_anthropic_usage(response: Any, *, provider: str, model: str) -> LeadAIUsage:
    usage = getattr(response, "usage", None)

    input_tokens = _coerce_int(_get_usage_value(usage, "input_tokens"))
    output_tokens = _coerce_int(_get_usage_value(usage, "output_tokens"))
    thinking_tokens = _coerce_int(_get_usage_value(usage, "thinking_tokens"))
    total_tokens = _coerce_int(_get_usage_value(usage, "total_tokens"))

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens + thinking_tokens

    other_tokens = max(total_tokens - input_tokens - output_tokens - thinking_tokens, 0)

    return LeadAIUsage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        other_tokens=other_tokens,
        total_tokens=total_tokens,
        raw={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        },
    )


def _extract_openai_compatible_chat_usage(response: Any, *, provider: str, model: str) -> LeadAIUsage:
    usage = getattr(response, "usage", None)

    input_tokens = _coerce_int(_get_usage_value(usage, "prompt_tokens"))
    if input_tokens <= 0:
        input_tokens = _coerce_int(_get_usage_value(usage, "input_tokens"))

    output_tokens = _coerce_int(_get_usage_value(usage, "completion_tokens"))
    if output_tokens <= 0:
        output_tokens = _coerce_int(_get_usage_value(usage, "output_tokens"))

    thinking_tokens = _coerce_int(_get_usage_value(usage, "completion_tokens_details.reasoning_tokens"))
    if thinking_tokens <= 0:
        thinking_tokens = _coerce_int(_get_usage_value(usage, "reasoning_tokens"))
    if thinking_tokens <= 0:
        thinking_tokens = _coerce_int(_get_usage_value(usage, "thinking_tokens"))

    total_tokens = _coerce_int(_get_usage_value(usage, "total_tokens"))
    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens

    other_tokens = max(total_tokens - input_tokens - output_tokens, 0)

    return LeadAIUsage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        other_tokens=other_tokens,
        total_tokens=total_tokens,
        raw={
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "reasoning_tokens": thinking_tokens,
            "total_tokens": total_tokens,
        },
    )


def _usage_from_dict(
    value: Any,
    *,
    fallback_provider: str,
    fallback_model: str,
) -> LeadAIUsage:
    if not isinstance(value, dict):
        return _empty_usage(provider=fallback_provider, model=fallback_model)

    return LeadAIUsage(
        provider=str(value.get("provider") or fallback_provider),
        model=str(value.get("model") or fallback_model),
        input_tokens=_coerce_int(value.get("input_tokens")),
        output_tokens=_coerce_int(value.get("output_tokens")),
        thinking_tokens=_coerce_int(value.get("thinking_tokens")),
        other_tokens=_coerce_int(value.get("other_tokens")),
        total_tokens=_coerce_int(value.get("total_tokens")),
        raw=dict(value.get("raw") or {}),
    )


def _combine_usage_profiles(
    *,
    main_usage: LeadAIUsage,
    assistant_usage: LeadAIUsage,
) -> LeadAIUsage:
    input_tokens = main_usage.input_tokens + assistant_usage.input_tokens
    output_tokens = main_usage.output_tokens + assistant_usage.output_tokens
    thinking_tokens = main_usage.thinking_tokens + assistant_usage.thinking_tokens
    other_tokens = main_usage.other_tokens + assistant_usage.other_tokens
    total_tokens = main_usage.total_tokens + assistant_usage.total_tokens

    if total_tokens <= 0:
        total_tokens = input_tokens + output_tokens + thinking_tokens + other_tokens

    return LeadAIUsage(
        provider="combined",
        model="main+assistant",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        other_tokens=other_tokens,
        total_tokens=total_tokens,
        raw={
            "main": main_usage.to_dict(),
            "assistant": assistant_usage.to_dict(),
        },
    )


def _empty_usage(*, provider: str, model: str) -> LeadAIUsage:
    return LeadAIUsage(
        provider=provider,
        model=model,
        raw={},
    )


def _get_usage_value(usage: Any, key: str) -> Any:
    if usage is None:
        return 0

    current = usage
    for part in key.split("."):
        if current is None:
            return 0

        if isinstance(current, dict):
            current = current.get(part, 0)
            continue

        current = getattr(current, part, 0)

    return current


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _lead_main_system_prompt() -> str:
    return (
        "You are the main smx-leads AI agent. Analyze the lead and return a final "
        "business-ready lead insight. Return JSON only."
    )


def _lead_assistant_system_prompt() -> str:
    return (
        "You are the assistant smx-leads AI agent. Extract narrow supporting context "
        "for the main lead-analysis agent. Return JSON only."
    )


def _lead_insight_schema() -> dict[str, Any]:
    return {
        "summary": "string",
        "category": "general_enquiry | demo_request | pilot_request | support_request | partnership | waitlist | sales | spam",
        "priority": "low | medium | high",
        "suggested_status": "new | reviewed | contacted | closed | spam",
        "recommended_action": "string",
        "draft_reply": "string",
        "spam_risk": "low | medium | high",
    }


def _lead_assistant_schema() -> dict[str, Any]:
    return {
        "summary": "string",
        "category": "string",
        "priority": "string",
        "spam_risk": "string",
        "key_points": ["string"],
        "recommended_focus": "string",
    }


def _build_agent_prompt(
    *,
    agent_name: str,
    system_prompt: str,
    task_prompt: str,
    expected_schema: dict[str, Any],
    context: dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            "You are running an internal smx-leads AI agent task.",
            f"Agent name: {agent_name}",
            "System instructions:",
            system_prompt.strip(),
            "Task:",
            task_prompt.strip(),
            "Expected JSON schema:",
            json.dumps(expected_schema, ensure_ascii=False, sort_keys=True),
            "Context:",
            json.dumps(context, ensure_ascii=False, sort_keys=True, default=str),
            "Return only one valid JSON object. Do not wrap it in Markdown. Do not include commentary.",
        ]
    )


def _parse_json_object(text: str, *, agent_name: str) -> dict[str, Any]:
    cleaned = _strip_markdown_json_fence(text.strip())

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LeadAIClientError(
            f"Agent {agent_name} returned invalid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise LeadAIClientError(
            f"Agent {agent_name} returned JSON that was not an object."
        )

    return parsed


def _strip_markdown_json_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S | re.I)
    if match:
        return match.group(1).strip()

    return text
