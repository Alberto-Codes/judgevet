"""Domain error types for Jev System One API."""

from __future__ import annotations


class JevError(Exception):
    """Base exception for all Jev-related errors.

    This is the parent class for all custom exceptions raised by this library.
    It ensures callers can catch all Jev errors with a single except clause
    without needing to import httpx.

    Attributes:
        message: The error message.
        status_code: The HTTP status code if available, None otherwise.
    """

    HTTP_STATUS_401_UNAUTHORIZED = 401
    HTTP_STATUS_403_FORBIDDEN = 403
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
        """
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:
        """Return string representation."""
        if self.status_code is not None:
            return f"{super().__str__()} (status {self.status_code})"
        return super().__str__()


class JevAuthError(JevError):
    """Authentication error - 401 or 403.

    Raised when the API key is missing, invalid, or lacks the necessary
    permissions to access the requested resource.

    Attributes:
        message: The error message.
        status_code: Always 401 or 403.
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the auth error.

        Args:
            message: The error message.
            status_code: The HTTP status code (401 or 403).
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


class JevRequestError(JevError):
    """Client request error - 4xx (except 401/403).

    Raised when the API rejects the request due to invalid parameters,
    malformed input, or other client-side issues.

    Attributes:
        message: The error message.
        status_code: The HTTP status code (4xx).
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the request error.

        Args:
            message: The error message.
            status_code: The HTTP status code (4xx).
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


class JevServiceError(JevError):
    """Server service error - 5xx or transport failures.

    Raised when the API returns a 5xx status code or when a transport
    error occurs (network issues, timeouts, etc.).

    Attributes:
        message: The error message.
        status_code: The HTTP status code (5xx) or None for transport errors.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the service error.

        Args:
            message: The error message.
            status_code: The HTTP status code (5xx) or None for transport errors.
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


class JevResponseError(JevError):
    """Response parsing error - 2xx with invalid body.

    Raised when the API returns a 2xx status code but the response body
    cannot be parsed into the expected domain types. This is particularly
    important because the domain model is inferred from documentation,
    so shape mismatches are expected when a live key exists.

    Attributes:
        message: The error message.
        status_code: Always 2xx.
    """

    def __init__(self, message: str, status_code: int) -> None:
        """Initialize the response error.

        Args:
            message: The error message.
            status_code: The HTTP status code (2xx).
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
