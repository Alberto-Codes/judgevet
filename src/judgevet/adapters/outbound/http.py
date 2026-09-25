"""HTTP outbound adapter with optional state redaction, gateway metadata and retries.

Error handling:
    The API error `detail` field is polymorphic:

    - Array for validation errors (422): [{"type", "loc", "msg", "input"}]
    - Object for auth errors (401/403): {"error_type", "message"}
    - Object for an oversized request (400 observed): {"error_type"} equal to
      "max_tokens_exceeded", raised as JevMaxTokensExceededError
    - Absent, malformed or unrecognised: falls back to status line alone.

    The `input` key in validation errors contains the caller's request payload
    and is deliberately excluded from error messages to avoid leaking user data.

Helper functions:
    - _build_payload: Build the request payload.
    - _parse_body: Parse the response body into a SystemOneResponse.
    - _read_error_detail: Read the message and wire error type of an error body.
    - _translate_status_error: Translate HTTP status errors to JevError subclasses.
    - _translate_request_error: Translate request errors to JevServiceError.
    - _convert_question_to_wire: Convert a Question object to its wire dict.

Examples:
    ```python
    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
    from judgevet.domain.questions import Noul
    from judgevet.domain.response import SystemOneResponse

    adapter = HTTPSystemOneAdapter(api_key="your-api-key")
    try:
        response: SystemOneResponse = adapter.system_one(
            state="Your content here",
            questions={
                "q1": Noul(instructions="Is this correct?"),
            },
        )
        print(response)
        print(response.model)
        print(response.answers)
    finally:
        adapter.close()
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.domain.errors][]: Error types
    - [judgevet.adapters.inbound.cli][]: CLI adapter
    - [judgevet.domain.response_parser][]: Response parsing

Raises:
    JevAuthError: If the API returns 401 or 403.
    JevRateLimitError: If the API returns 429 (rate limit exceeded).
    JevMaxTokensExceededError: If a 4xx body reports `max_tokens_exceeded`.
    JevRequestError: If the API returns 4xx (except 401/403, 429).
    JevServiceError: If the API returns 5xx or a transport error occurs.
    JevResponseError: If the API returns 2xx with unparseable body.

Async adapters:
    AsyncSystemOnePort: Async protocol for the System One API.
    AsyncHTTPSystemOneAdapter: Async HTTP adapter using httpx.AsyncClient.

    The async adapter provides `aclose()`, `__aenter__`, and `__aexit__` for
    lifecycle management. It does NOT provide sync names (`close`, `__enter__`,
    `__exit__`) because calling `self._client.aclose()` without `await` would
    return an un-awaited coroutine and close nothing silently. An AttributeError
    is the better failure.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self, Unpack

import httpx

from judgevet.adapters.outbound.gateway import (
    RequestMetadata,
    configured_gateway,
)
from judgevet.adapters.outbound.http_events import CallEvent, call_event
from judgevet.adapters.outbound.network import NetworkConfig
from judgevet.adapters.outbound.request_body import (
    AdapterOptions,
    configured_redactor,
    prepare_body,
)
from judgevet.adapters.outbound.retries import RetryPolicy
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevMaxTokensExceededError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.response_parser import parse_system_one_response


def _extract_error_detail(detail: Any) -> str:
    """Extract a message only from recognized, well-formed diagnostic fields.

    The detail field can be:
    - An array of validation errors: [{"type", "loc", "msg", "input"}]
    - An object for auth errors: {"error_type", "message"}
    - Something else (treat as unknown)

    Never includes the "input" field as it contains caller content. Invalid
    field shapes discard the entire detail rather than stringify containers.

    Args:
        detail: The detail field from the error response body.

    Returns:
        A formatted error message, or empty string if detail is unknown.
    """
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if not isinstance(item, dict):
                return ""
            type_part = item.get("type", "unknown_type")
            location = item.get("loc", [])
            msg_part = item.get("msg", "no message")
            if (
                not isinstance(type_part, str)
                or not isinstance(msg_part, str)
                or not isinstance(location, list)
                or any(type(part) not in (str, int) for part in location)
            ):
                return ""
            loc_part = ".".join(str(part) for part in location)
            if loc_part:
                parts.append(f"{type_part} at {loc_part}: {msg_part}")
            else:
                parts.append(f"{type_part}: {msg_part}")
        return "; ".join(parts)
    if isinstance(detail, dict):
        error_type = detail.get("error_type", "")
        message = detail.get("message", "")
        if not isinstance(error_type, str) or not isinstance(message, str):
            return ""
        return ": ".join(part for part in (error_type, message) if part)
    return ""


def _convert_question_to_wire(question: Any) -> Any:
    """Convert a Question object to its wire dict format.

    The wire format is:
        - noul:   {"type": "noul",   "instructions": ..., "criteria": {...} or None}
        - choice: {"type": "choice", "instructions": ..., "criteria": {...} or None}
        - score:  {"type": "score",  "instructions": ..., "criteria": [...]  or None}

    A key whose value is None is omitted from the output.

    Args:
        question: A Question object or a raw dict. Non-Question values pass through.

    Returns:
        A wire dict for Question objects, or the original value otherwise.
    """
    if isinstance(question, Noul):
        result: dict[str, Any] = {"type": "noul"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    elif isinstance(question, Choice):
        result = {"type": "choice"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    elif isinstance(question, Score):
        result = {"type": "score"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    # Non-Question values pass through untouched
    return question


def _build_payload(
    state: str | dict[str, Any] | list[Any],
    questions: Mapping[str, Any],
    model: str | None,
    default_model: str,
) -> dict[str, Any]:
    """Build the request payload for the System One API.

    Args:
        state: The content to evaluate.
        questions: Mapping of question names to question definitions.
            Both Question objects and raw dicts are accepted; mixed mappings
            are allowed. Question objects are converted to their wire format.
        model: Model name override, or None to use the default.
        default_model: Default model to use when model is None.

    Returns:
        A dictionary with keys "state", "questions", and "model".
    """
    converted_questions = {
        name: _convert_question_to_wire(value) for name, value in questions.items()
    }
    return {
        "state": state,
        "questions": converted_questions,
        "model": model or default_model,
    }


def _parse_body(response: httpx.Response) -> SystemOneResponse:
    """Parse the JSON response body into a SystemOneResponse.

    Args:
        response: The HTTP response from the API.

    Returns:
        A parsed SystemOneResponse.

    Raises:
        JevResponseError: If the response body is not valid JSON.
    """
    try:
        raw = response.json()
    except ValueError as exc:
        raise JevResponseError(
            f"Failed to parse response body: {exc}",
            response.status_code,
        ) from exc
    return parse_system_one_response("system-one", raw)


def _read_error_detail(exc: httpx.HTTPStatusError) -> tuple[str, str]:
    """Read the error message and the wire error type from an error body.

    Args:
        exc: The HTTP status error whose response body is read.

    Returns:
        The message, with any extracted detail appended, and the string
        `detail.error_type`, or an empty string when the body carries none.
    """
    error_message = str(exc)
    error_type = ""
    try:
        body = exc.response.json()
    except ValueError:
        return error_message, error_type  # Body is not JSON
    detail = body.get("detail") if isinstance(body, dict) else None
    if detail is not None:
        extracted = _extract_error_detail(detail)
        if extracted:
            error_message = f"{exc!s}; {extracted}"
    if isinstance(detail, dict) and isinstance(detail.get("error_type"), str):
        error_type = detail["error_type"]
    return error_message, error_type


def _translate_status_error(
    exc: httpx.HTTPStatusError,
) -> JevError | None:
    """Translate an httpx.HTTPStatusError to a JevError subclass.

    A 4xx body whose `detail.error_type` is `max_tokens_exceeded` becomes
    JevMaxTokensExceededError. One live call returned that marker with 400.
    Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575.

    Args:
        exc: The HTTP status error to translate.

    Returns:
        A JevError subclass instance for status codes 429, 401, 403, 4xx, or 5xx.
        None for unhandled status codes (e.g., 3xx).
    """
    status_code = exc.response.status_code
    error_message, error_type = _read_error_detail(exc)

    if status_code == JevError.HTTP_STATUS_429_TOO_MANY_REQUESTS:
        return JevRateLimitError(error_message, status_code)
    elif status_code in (
        JevError.HTTP_STATUS_401_UNAUTHORIZED,
        JevError.HTTP_STATUS_403_FORBIDDEN,
    ):
        return JevAuthError(error_message, status_code)
    elif JevError.HTTP_STATUS_400_MIN <= status_code < JevError.HTTP_STATUS_500_MIN:
        if error_type == JevMaxTokensExceededError.WIRE_ERROR_TYPE:
            return JevMaxTokensExceededError(error_message, status_code)
        return JevRequestError(error_message, status_code)
    elif status_code >= JevError.HTTP_STATUS_500_MIN:
        return JevServiceError(error_message, status_code)
    # Unhandled status code (e.g., 3xx)
    return None


def _translate_request_error(exc: httpx.RequestError) -> JevServiceError:
    """Translate an httpx.RequestError to a JevServiceError.

    Args:
        exc: The request error to translate.

    Returns:
        A JevServiceError with the original error message and status_code=None.
    """
    return JevServiceError(str(exc), None)


class HTTPSystemOneAdapter:
    """HTTP adapter with explicit network configuration and opt-in retries.

    This class satisfies SystemOnePort structurally without importing it.
    See: https://api.typesafe.ai/v1/systemone

    See: https://api.typesafe.ai/v1/systemone

    Attributes:
        api_key (str | None): The TypeSafe API key.
        base_url (str): The API base URL.
        default_model (str): The default model to use.

    Raises:
        JevAuthError: If the API returns 401 or 403.
        JevRateLimitError: If the API returns 429 (rate limit exceeded).
        JevMaxTokensExceededError: If a 4xx body reports `max_tokens_exceeded`.
        JevRequestError: If the API returns 4xx (except 401/403, 429).
        JevServiceError: If the API returns 5xx or a transport error occurs.
        JevResponseError: If the API returns 2xx with unparseable body.

    Error details:
        Validation errors (422) include an array of error objects. Each
        object's `input` key contains the caller's request payload. The adapter
        deliberately omits this key from the error message.

        Auth errors (401/403) return an object with `error_type` and
        `message` fields.

        Unknown detail shapes fall back to the HTTP status line alone.

        Transport errors (timeouts, connection failures) are mapped to
        `JevServiceError` with `status_code=None` and `retryable=True`.
        A `retryable=True` timeout is advisory: retrying a read timeout
        may be double-billed because the service may still be processing
        the first attempt.

    Examples:
        ```python
        adapter = HTTPSystemOneAdapter(api_key="your-api-key")
        try:
            response: SystemOneResponse = adapter.system_one(
                state="Your content here",
                questions={"q1": {"type": "noul", "instructions": "Is this correct?"}},
            )
            print(response)
        finally:
            adapter.close()
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "jev-latest",
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30.0,
        *,
        retry: RetryPolicy | None = None,
        network: NetworkConfig | None = None,
        **options: Unpack[AdapterOptions],
    ) -> None:
        """Initialize the HTTP adapter.

        Args:
            api_key: TypeSafe API key.
            base_url: API base URL. Defaults to https://api.typesafe.ai.
            default_model: Default model to use. Defaults to jev-latest.
            transport: Optional httpx transport for testing. Defaults to None.
            timeout_seconds: Read timeout in seconds. Defaults to 30.0.
            retry: Validated retry policy. None preserves one attempt.
            network: Proxy and TLS options. None retains HTTPX defaults.

        Other Parameters:
            gateway (GatewayConfig | None): Explicit authentication and metadata.
                Omission retains direct defaults.
            redactor (StateRedactor | None): Synchronous caller-owned state transformation.
                Omission preserves state and the existing serialization path.

        Raises:
            ValueError: If the key is absent, timeout is nonpositive, or the CA bundle cannot load.
        """
        self._api_key = api_key
        if self._api_key is None:
            raise ValueError("API key must be provided")

        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {timeout_seconds}")

        self._retry = retry or RetryPolicy()
        self._redactor = configured_redactor(options)
        self._gateway = configured_gateway({"gateway": options.get("gateway")})
        network = network or NetworkConfig()
        self._base_url = base_url or "https://api.typesafe.ai"
        self._default_model = default_model
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=self._gateway.authentication(self._api_key),
            transport=transport,
            proxy=network.proxy,
            verify=network.verification(),
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str | None = None,
        *,
        metadata: RequestMetadata | None = None,
    ) -> SystemOneResponse:
        """Prepare optional redaction once, call Jev and emit terminal metadata.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Model name override.
            metadata: Explicit per-call headers overriding gateway defaults.

        Returns:
            Typed SystemOneResponse with parsed answer objects.

        Raises:
            ValueError: If metadata or redacted JSON violates input rules.
            Exception: If a configured redactor or its input copy fails before IO.
            JevAuthError: If the API returns 401 or 403.
            JevRateLimitError: If the API returns 429 (rate limit exceeded).
            JevMaxTokensExceededError: If a 4xx body reports `max_tokens_exceeded`.
            JevRequestError: If the API returns 4xx (except 401/403, 429).
            JevServiceError: If the API returns 5xx or a transport error occurs.
            JevResponseError: If the API returns 2xx with unparseable body.

        Error details:
            Validation errors (422) include an array of error objects. Each
            object's `input` key contains the caller's request payload. The adapter
            deliberately omits this key from the error message.

            Auth errors (401/403) return an object with `error_type` and
            `message` fields.

            Unknown detail shapes fall back to the HTTP status line alone.

            Transport errors (timeouts, connection failures) are mapped to
            `JevServiceError` with `status_code=None` and `retryable=True`.
            A `retryable=True` timeout is advisory: retrying a read timeout
            may be double-billed because the service may still be processing
            the first attempt.

        Implementation notes:
            Uses helper functions for payload building, response parsing,
            and error translation to ensure consistent behavior across adapters.
        """
        with call_event(model or self._default_model, len(questions)) as event:
            headers = self._gateway.request_headers(metadata)
            payload = prepare_body(
                _build_payload(state, questions, model, self._default_model),
                self._redactor,
            )
            answer = self._retry.run(lambda: self._request(payload, event, headers))
            event.resolved_model = answer.model
            event.input_tokens = answer.usage.input_tokens
            event.output_tokens = answer.usage.output_tokens
            event.outcome = "success"
            return answer

    def _request(
        self, payload: dict[str, Any] | bytes, event: CallEvent, headers: dict[str, str]
    ) -> SystemOneResponse:
        """Send one attempt and translate HTTP errors.

        Args:
            payload: Existing JSON data or a redacted immutable body snapshot.
            event: Terminal metadata for this logical call.
            headers: Validated metadata snapshot shared by every attempt.

        Returns:
            Parsed judgment response.

        Raises:
            JevError: If the service or transport rejects the request.
            httpx.HTTPStatusError: If an unhandled HTTP status occurs.
        """
        event.status_code = None
        try:
            response = self._client.post(
                "/v1/systemone",
                json=None if isinstance(payload, bytes) else payload,
                content=payload if isinstance(payload, bytes) else None,
                headers=headers,
            )
            event.status_code = response.status_code
            response.raise_for_status()
            return _parse_body(response)
        except httpx.HTTPStatusError as exc:
            translated = _translate_status_error(exc)
            if translated is None:
                raise
            raise translated from exc
        except httpx.RequestError as exc:
            raise _translate_request_error(exc) from exc

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()


class AsyncHTTPSystemOneAdapter:
    """Async HTTP adapter with explicit network configuration and bounded retries.

    This class satisfies AsyncSystemOnePort structurally without importing it.
    See: https://api.typesafe.ai/v1/systemone

    Note:
        This adapter provides `aclose()`, `__aenter__`, and `__aexit__` for
        lifecycle management. It does NOT provide sync names (`close`,
        `__enter__`, `__exit__`) because calling `self._client.aclose()`
        without `await` would return an un-awaited coroutine and close nothing
        silently. An AttributeError is the better failure.

    Attributes:
        api_key (str | None): The TypeSafe API key.
        base_url (str): The API base URL.
        default_model (str): The default model to use.

    Raises:
        JevAuthError: If the API returns 401 or 403.
        JevRateLimitError: If the API returns 429 (rate limit exceeded).
        JevMaxTokensExceededError: If a 4xx body reports `max_tokens_exceeded`.
        JevRequestError: If the API returns 4xx (except 401/403, 429).
        JevServiceError: If the API returns 5xx or a transport error occurs.
        JevResponseError: If the API returns 2xx with unparseable body.

    Error details:
        Validation errors (422) include an array of error objects. Each
        object's `input` key contains the caller's request payload. The adapter
        deliberately omits this key from the error message.

        Auth errors (401/403) return an object with `error_type` and
        `message` fields.

        Unknown detail shapes fall back to the HTTP status line alone.

        Transport errors (timeouts, connection failures) are mapped to
        `JevServiceError` with `status_code=None` and `retryable=True`.
        A `retryable=True` timeout is advisory: retrying a read timeout
        may be double-billed because the service may still be processing
        the first attempt.

    Examples:
        ```python
        async def main() -> SystemOneResponse:
            adapter = AsyncHTTPSystemOneAdapter(api_key="your-api-key")
            try:
                response: SystemOneResponse = await adapter.system_one(
                    state="Your content here",
                    questions={
                        "q1": {"type": "noul", "instructions": "Is this correct?"}
                    },
                )
                print(response)
                return response
            finally:
                await adapter.aclose()
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "jev-latest",
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 30.0,
        *,
        retry: RetryPolicy | None = None,
        network: NetworkConfig | None = None,
        **options: Unpack[AdapterOptions],
    ) -> None:
        """Initialize the async HTTP adapter.

        Args:
            api_key: TypeSafe API key.
            base_url: API base URL. Defaults to https://api.typesafe.ai.
            default_model: Default model to use. Defaults to jev-latest.
            transport: Optional httpx async transport for testing. Defaults to None.
            timeout_seconds: Read timeout in seconds. Defaults to 30.0.
            retry: Validated retry policy. None preserves one attempt.
            network: Proxy and TLS options. None retains HTTPX defaults.

        Other Parameters:
            gateway (GatewayConfig | None): Explicit authentication and metadata.
                Omission retains direct defaults.
            redactor (StateRedactor | None): Synchronous caller-owned state transformation.
                Omission preserves state and the existing serialization path.

        Raises:
            ValueError: If the key is absent, timeout is nonpositive, or the CA bundle cannot load.
        """
        if api_key is None:
            raise ValueError("API key must be provided")

        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {timeout_seconds}")

        self._api_key = api_key
        self._retry = retry or RetryPolicy()
        self._redactor = configured_redactor(options)
        self._gateway = configured_gateway({"gateway": options.get("gateway")})
        network = network or NetworkConfig()
        self._base_url = base_url or "https://api.typesafe.ai"
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._gateway.authentication(self._api_key),
            transport=transport,
            proxy=network.proxy,
            verify=network.verification(),
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str | None = None,
        *,
        metadata: RequestMetadata | None = None,
    ) -> SystemOneResponse:
        """Prepare optional redaction once, then await bounded HTTP attempts.

        Args:
            state: The content to evaluate.
            questions: Mapping of question names to question definitions.
            model: Model name override.
            metadata: Explicit per-call headers overriding gateway defaults.

        Returns:
            Typed SystemOneResponse with parsed answer objects.

        Raises:
            ValueError: If metadata or redacted JSON violates input rules.
            Exception: If a configured redactor or its input copy fails before IO.
            JevAuthError: If the API returns 401 or 403.
            JevRateLimitError: If the API returns 429 (rate limit exceeded).
            JevMaxTokensExceededError: If a 4xx body reports `max_tokens_exceeded`.
            JevRequestError: If the API returns 4xx (except 401/403, 429).
            JevServiceError: If the API returns 5xx or a transport error occurs.
            JevResponseError: If the API returns 2xx with unparseable body.

        Error details:
            Validation errors (422) include an array of error objects. Each
            object's `input` key contains the caller's request payload. The adapter
            deliberately omits this key from the error message.

            Auth errors (401/403) return an object with `error_type` and
            `message` fields.

            Unknown detail shapes fall back to the HTTP status line alone.

            Transport errors (timeouts, connection failures) are mapped to
            `JevServiceError` with `status_code=None` and `retryable=True`.
            A `retryable=True` timeout is advisory: retrying a read timeout
            may be double-billed because the service may still be processing
            the first attempt.
        """
        with call_event(model or self._default_model, len(questions)) as event:
            headers = self._gateway.request_headers(metadata)
            payload = prepare_body(
                _build_payload(state, questions, model, self._default_model),
                self._redactor,
            )
            answer = await self._retry.arun(
                lambda: self._request(payload, event, headers)
            )
            event.resolved_model = answer.model
            event.input_tokens = answer.usage.input_tokens
            event.output_tokens = answer.usage.output_tokens
            event.outcome = "success"
            return answer

    async def _request(
        self, payload: dict[str, Any] | bytes, event: CallEvent, headers: dict[str, str]
    ) -> SystemOneResponse:
        """Send one attempt and translate HTTP errors.

        Args:
            payload: Existing JSON data or a redacted immutable body snapshot.
            event: Terminal metadata for this logical call.
            headers: Validated metadata snapshot shared by every attempt.

        Returns:
            Parsed judgment response.

        Raises:
            JevError: If the service or transport rejects the request.
            httpx.HTTPStatusError: If an unhandled HTTP status occurs.
        """
        event.status_code = None
        try:
            response = await self._client.post(
                "/v1/systemone",
                json=None if isinstance(payload, bytes) else payload,
                content=payload if isinstance(payload, bytes) else None,
                headers=headers,
            )
            event.status_code = response.status_code
            response.raise_for_status()
            return _parse_body(response)
        except httpx.HTTPStatusError as exc:
            translated = _translate_status_error(exc)
            if translated is None:
                raise
            raise translated from exc
        except httpx.RequestError as exc:
            raise _translate_request_error(exc) from exc

    async def aclose(self) -> None:
        """Close the HTTP async client."""
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.aclose()
