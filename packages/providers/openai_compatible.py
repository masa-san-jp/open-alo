"""OpenAI Chat Completions-compatible decision provider."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from .capabilities import ProviderCapabilities
from .errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from .normalize import normalize_binary, normalize_categorical, normalize_scalar
from .retry import call_with_retry


class OpenAICompatibleProvider:
    """Decision provider for OpenAI Chat Completions-compatible HTTP APIs.

    ``transport`` is a useful dependency-injection seam for tests and local
    integrations. It receives the JSON request payload and must return the
    parsed JSON response payload. A transport may raise
    :class:`ProviderTimeoutError` or :class:`ProviderRateLimitError` directly;
    plain ``TimeoutError`` and exceptions with an HTTP status of 429 are also
    converted to those provider errors before retry handling.
    """

    name = "openai-compatible"
    capabilities = ProviderCapabilities(
        decision_types=frozenset({"binary", "categorical", "scalar"})
    )

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.config = config
        self._transport = transport or self._default_transport

    def binary(
        self, decision_id: str, state: dict[str, Any], question: str
    ) -> dict[str, float]:
        payload = self._build_payload(
            decision_id=decision_id,
            state=state,
            question=question,
            instruction='Return only JSON in the form {"p_true": <float from 0 to 1>}.',
        )
        response = self._call_transport_with_retry(payload)
        result = self._decode_result(response)
        if "p_true" not in result:
            raise ProviderResponseError("binary response is missing expected key 'p_true'")

        p_true = float(result["p_true"])
        p_false = float(result.get("p_false", 1.0 - p_true))
        return normalize_binary(p_true, p_false)

    def categorical(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        options: list[str],
    ) -> dict[str, float]:
        payload = self._build_payload(
            decision_id=decision_id,
            state=state,
            question=question,
            instruction=(
                "Return only a JSON object with one float probability for every "
                f"declared option: {json.dumps(options, ensure_ascii=False)}."
            ),
            extra={"options": options},
        )
        response = self._call_transport_with_retry(payload)
        result = self._decode_result(response)
        expected = set(options)
        actual = set(result)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            details = []
            if missing:
                details.append(f"missing keys {missing}")
            if extra:
                details.append(f"unexpected keys {extra}")
            raise ProviderResponseError(
                "categorical response must contain exactly the declared options ("
                + ", ".join(details)
                + ")"
            )

        probabilities = {option: float(result[option]) for option in options}
        return normalize_categorical(probabilities)

    def scalar(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        scale: dict[str, Any],
    ) -> dict[str, float]:
        payload = self._build_payload(
            decision_id=decision_id,
            state=state,
            question=question,
            instruction=(
                'Return only JSON in the form '
                '{"score": <float within scale>, "confidence": <float from 0 to 1>}. '
                f"The scale is {json.dumps(scale, ensure_ascii=False, sort_keys=True)}."
            ),
            extra={"scale": scale},
        )
        response = self._call_transport_with_retry(payload)
        result = self._decode_result(response)
        missing = [key for key in ("score", "confidence") if key not in result]
        if missing:
            raise ProviderResponseError(
                f"scalar response is missing expected keys {missing}"
            )

        return normalize_scalar(result["score"], result["confidence"], scale)

    def _build_payload(
        self,
        *,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        instruction: str,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {
            "decision_id": decision_id,
            "question": question,
            "state": state,
        }
        if extra:
            context.update(extra)
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a decision provider. Answer only with one valid JSON "
                        "object and no markdown or explanation. "
                        + instruction
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, sort_keys=True),
                },
            ],
            "temperature": 0,
        }

    def _call_transport_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        return call_with_retry(lambda: self._call_transport(payload))

    def _call_transport(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._transport(payload)
        except (ProviderTimeoutError, ProviderRateLimitError):
            raise
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError("OpenAI-compatible request timed out") from error
        except Exception as error:
            if _http_status(error) == 429:
                raise ProviderRateLimitError(
                    "OpenAI-compatible request was rate limited"
                ) from error
            raise

        if not isinstance(response, Mapping):
            raise ProviderResponseError(
                "OpenAI-compatible transport must return a response mapping"
            )
        return dict(response)

    def _decode_result(self, response: Mapping[str, Any]) -> dict[str, Any]:
        try:
            choices = response["choices"]
            first_choice = choices[0]
            message = first_choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderResponseError(
                "chat-completion response is missing choices[0].message.content"
            ) from error

        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError(
                "chat-completion response content is missing or not text"
            )
        try:
            result = json.loads(content)
        except (TypeError, ValueError) as error:
            raise ProviderResponseError(
                "chat-completion response content is not valid JSON"
            ) from error
        if not isinstance(result, dict):
            raise ProviderResponseError("chat-completion JSON content must be an object")
        return result

    def _default_transport(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key is not None
                    else {}
                ),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 429:
                raise ProviderRateLimitError(
                    "OpenAI-compatible request was rate limited"
                ) from error
            raise ProviderResponseError(
                f"OpenAI-compatible HTTP request failed with status {error.code}"
            ) from error
        except (socket.timeout, TimeoutError) as error:
            raise ProviderTimeoutError("OpenAI-compatible request timed out") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise ProviderTimeoutError(
                    "OpenAI-compatible request timed out"
                ) from error
            raise ProviderError("OpenAI-compatible request failed") from error

        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, TypeError, ValueError) as error:
            raise ProviderResponseError(
                "OpenAI-compatible HTTP response body is not valid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise ProviderResponseError(
                "OpenAI-compatible HTTP response body must be a JSON object"
            )
        return parsed


def _http_status(error: BaseException) -> int | None:
    """Read a conventional status attribute from a fake transport error."""

    for attribute in ("status", "status_code", "code"):
        status = getattr(error, attribute, None)
        if status is not None:
            try:
                return int(status)
            except (TypeError, ValueError):
                return None
    return None
