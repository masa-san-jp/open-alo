"""Optional natural-language ALO drafting assistant."""

from __future__ import annotations

import re

from packages.providers.openai_compatible import OpenAICompatibleProvider


class AssistantError(ValueError):
    """Raised when an assistant request is not meaningful."""


SYSTEM_PROMPT = """You draft Open ALO YAML documents for Draft 0.1.
Return ONLY the YAML document: no Markdown fences, no explanation, and no
introductory text. The document must have a top-level `alo` mapping with these
required fields: `spec_version` exactly "0.1", `id`, `version`, `purpose`,
`inputs`, `state_schema`, `decisions`, `transition_rules`, and `outputs`.
Each input is a mapping with `type` and boolean `required`. Each state field
has `type`, `initial`, and `updated_by`. Each decision has `id`, a `type` of
`binary`, `categorical`, or `scalar`, `reads`, and `question`; categorical
decisions also have non-empty `options`, and scalar decisions also have a
numeric `scale` with `min` and `max`. Each transition rule has `id`, unique
integer `priority`, `when`, and `set`, and may have `stop_condition`. Outputs
are explicit fields. Optional useful fields include `thresholds`,
`derived_values`, and `stop_conditions`. Keep references and rule assignments
consistent, and make the result a plausible, concise, self-contained draft.
"""


def draft_alo(
    description: str,
    *,
    model: str,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
    transport=None,
) -> str:
    """Ask an OpenAI-compatible endpoint for an ALO draft."""

    if not isinstance(description, str) or not description.strip():
        raise AssistantError("description must not be empty")
    provider = OpenAICompatibleProvider(
        model=model,
        api_key=api_key,
        base_url=base_url,
        transport=transport,
    )
    return _strip_code_fence(provider.complete(SYSTEM_PROMPT, description))


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.fullmatch(
        r"```(?:yaml|yml|json)?\s*\n?(.*?)\n?\s*```",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else text


__all__ = ["AssistantError", "draft_alo"]
