"""Domain error types for Jev System One API.

Examples:
    ```python
    from judgevet.domain.errors import (
        JevAuthError,
        JevError,
        JevMaxTokensExceededError,
        JevRequestError,
        JevResponseError,
        JevServiceError,
    )

    try:
        # Your API call here
        pass
    except JevAuthError as exc:
        # Handle authentication errors
        if exc.retryable:
            # Retry with backoff
            pass
    except JevMaxTokensExceededError as exc:
        # Shrink the state or the longest question (do not retry)
        pass
    except JevRequestError as exc:
        # Handle client request errors (do not retry)
        pass
    except JevServiceError as exc:
        # Handle service errors
        if exc.retryable:
            # Retry with backoff
            pass
    except JevError as exc:
        # Handle all other Jev errors
        pass
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.adapters.outbound.http][]: HTTP adapter

Attributes:
    JevError (type): Base exception for all Jev errors.
    JevAuthError (type): 401/403 authentication errors.
    JevRequestError (type): 4xx client request errors.
    JevMaxTokensExceededError (type): Request over a service token budget.
    JevResponseError (type): 2xx with unparseable body.
    JevServiceError (type): 5xx or transport errors.
"""

from __future__ import annotations


class JevError(Exception):
    """Base exception for all Jev-related errors.

    This is the parent of the service-error hierarchy, not local policy errors
    or every HTTPX exception. Redirects can propagate raw HTTPX status errors.
    The base class always reports retryable=False; subclasses override it.

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int | None): The HTTP status code if available, None otherwise.
        retryable (bool): Advisory retry classification; False on this base class.

    Examples:
        ```python
        error = JevError("Something went wrong", 500)
        assert error.retryable is False
        ```
    """

    HTTP_STATUS_401_UNAUTHORIZED = 401
    HTTP_STATUS_403_FORBIDDEN = 403
    HTTP_STATUS_429_TOO_MANY_REQUESTS = 429
    HTTP_STATUS_400_MIN = 400
    HTTP_STATUS_499_MAX = 499
    HTTP_STATUS_500_MIN = 500
    HTTP_STATUS_599_MAX = 599
    HTTP_STATUS_200_MIN = 200
    HTTP_STATUS_299_MAX = 299

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            status_code: The HTTP status code if available.

        Examples:
            ```python
            error = JevError("Something went wrong", 500)
            assert error.retryable is False
            ```
        """
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:
        """Return string representation."""
        if self.status_code is not None:
            return f"{super().__str__()} (status {self.status_code})"
        return super().__str__()

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            False on this base class, independent of status_code.
        """
        return False


class JevAuthError(JevError):
    """Authentication error - 401 or 403.

    Raised when the API key is missing, invalid, or lacks the necessary
    permissions to access the requested resource.

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int): Always 401 or 403.

    Examples:
        ```python
        error = JevAuthError("Unauthorized", 401)
        assert error.retryable is False
        ```
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the auth error.

        Args:
            message: The error message.
            status_code: The HTTP status code (401 or 403).

        Raises:
            ValueError: If status_code is not 401 or 403.
        """
        is_auth_status = status_code in (
            JevError.HTTP_STATUS_401_UNAUTHORIZED,
            JevError.HTTP_STATUS_403_FORBIDDEN,
        )
        if not is_auth_status:
            raise ValueError(
                "JevAuthError status code must be "
                f"{JevError.HTTP_STATUS_401_UNAUTHORIZED} or "
                f"{JevError.HTTP_STATUS_403_FORBIDDEN}"
            )
        super().__init__(message, status_code)

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            False for auth errors (401, 403).
        """
        return False


class JevRequestError(JevError):
    """Client request error - 4xx (except 401/403).

    Raised when the API rejects the request due to invalid parameters,
    malformed input, or other client-side issues.

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int): The HTTP status code (4xx).

    Examples:
        ```python
        error = JevRequestError("Bad Request", 400)
        assert error.retryable is False
        ```
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the request error.

        Args:
            message: The error message.
            status_code: The HTTP status code (4xx).

        Raises:
            ValueError: If status_code is not a 4xx code or is 401/403.
        """
        is_4xx = (
            JevError.HTTP_STATUS_400_MIN <= status_code < JevError.HTTP_STATUS_500_MIN
        )
        is_auth = status_code in (
            JevError.HTTP_STATUS_401_UNAUTHORIZED,
            JevError.HTTP_STATUS_403_FORBIDDEN,
        )
        if not is_4xx or is_auth:
            raise ValueError(
                "JevRequestError status code must be "
                f"{JevError.HTTP_STATUS_400_MIN}-{JevError.HTTP_STATUS_499_MAX} "
                f"excluding {JevError.HTTP_STATUS_401_UNAUTHORIZED}/"
                f"{JevError.HTTP_STATUS_403_FORBIDDEN}"
            )
        super().__init__(message, status_code)

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            False for request errors (4xx).
        """
        return False


class JevMaxTokensExceededError(JevRequestError):
    """Oversized request - the service reported `max_tokens_exceeded`.

    The HTTP adapter raises this error when an error body carries
    `detail.error_type` equal to `max_tokens_exceeded`. One live call returned
    that marker with status 400. The adapter matches the marker, not the status.
    The body does not say which token budget the request exceeded.
    Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575.
    The vendor states a 64k-token request budget and a 32k-token budget for
    `state` plus the longest question.
    Source: https://docs.typesafe.ai/models.md.

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int): The HTTP status code (4xx); 400 in the observed call.
        WIRE_ERROR_TYPE (str): The `detail.error_type` marker the adapter matches.

    Examples:
        ```python
        error = JevMaxTokensExceededError("max_tokens_exceeded", 400)
        assert isinstance(error, JevRequestError)
        assert error.retryable is False
        ```
    """

    WIRE_ERROR_TYPE = "max_tokens_exceeded"

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            False: the same oversized request fails again.
        """
        return False


class JevServiceError(JevError):
    """Server service error - 5xx or transport failures.

    Raised when the API returns a 5xx status code or when a transport
    error occurs (network issues, timeouts, etc.).

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int | None): The HTTP status code (5xx) or None for transport errors.

    Examples:
        ```python
        error = JevServiceError("Internal Server Error", 500)
        assert error.retryable is True
        ```
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the service error.

        Args:
            message: The error message.
            status_code: The HTTP status code (5xx) or None for transport errors.

        Raises:
            ValueError: If status_code is not a 5xx code when provided.
        """
        if status_code is not None and not (
            JevError.HTTP_STATUS_500_MIN
            <= status_code
            < JevError.HTTP_STATUS_599_MAX + 1
        ):
            raise ValueError(
                "JevServiceError status code must be "
                f"{JevError.HTTP_STATUS_500_MIN}-{JevError.HTTP_STATUS_599_MAX} or None"
            )
        super().__init__(message, status_code)

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            True for service errors (5xx) and transport failures (status None).
        """
        return True


class JevRateLimitError(JevError):
    """Rate limit exceeded - 429.

    Raised when the API returns a 429 status code indicating the client
    has exceeded the rate limit. The caller chooses retry limits; the adapter
    defaults to one attempt.

    See: https://docs.typesafe.ai/api.md

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int): Always 429.

    Examples:
        ```python
        error = JevRateLimitError("Rate limit exceeded", 429)
        assert error.retryable is True
        ```
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the rate limit error.

        Args:
            message: The error message.
            status_code: The HTTP status code (must be 429).

        Raises:
            ValueError: If status_code is not 429.
        """
        if status_code != JevError.HTTP_STATUS_429_TOO_MANY_REQUESTS:
            raise ValueError(
                "JevRateLimitError status code must be "
                f"{JevError.HTTP_STATUS_429_TOO_MANY_REQUESTS}"
            )
        super().__init__(message, status_code)

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            True for rate limit errors (429).
        """
        return True


class JevResponseError(JevError):
    """Response parsing error - 2xx with invalid body.

    Raised when the API returns a 2xx status code but the response body
    cannot be parsed into the expected domain types. This is a local parsing
    failure. Live calls verify only the fields they exercised;
    other fields remain inferred from documentation.

    Attributes:
        args (tuple): Standard exception arguments containing the message.
        status_code (int): Always 2xx.

    Examples:
        ```python
        error = JevResponseError("Parse error", 200)
        assert error.retryable is False
        ```
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the response error.

        Args:
            message: The error message.
            status_code: The HTTP status code (2xx).

        Raises:
            ValueError: If status_code is not a 2xx code.
        """
        if not (
            JevError.HTTP_STATUS_200_MIN
            <= status_code
            < JevError.HTTP_STATUS_299_MAX + 1
        ):
            raise ValueError(
                "JevResponseError status code must be "
                f"{JevError.HTTP_STATUS_200_MIN}-{JevError.HTTP_STATUS_299_MAX}"
            )
        super().__init__(message, status_code)

    @property
    def retryable(self) -> bool:
        """Return True if the error is retryable.

        Returns:
            False for response errors (2xx with invalid body).
        """
        return False
