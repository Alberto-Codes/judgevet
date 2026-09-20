"""Unit tests for domain error types."""

from __future__ import annotations

import pytest

from jev_client.domain.errors import (
    JevAuthError,
    JevError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)


class TestJevError:
    """Tests for JevError base class."""

    def test_init_with_message_only(self) -> None:
        """Test initialization with message only."""
        error = JevError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.status_code is None

    def test_init_with_status_code(self) -> None:
        """Test initialization with status code."""
        error = JevError("Not found", 404)
        assert "Not found (status 404)" in str(error)
        assert error.status_code == 404


class TestJevAuthError:
    """Tests for JevAuthError."""

    def test_init_with_401(self) -> None:
        """Test initialization with 401 status code."""
        error = JevAuthError("Unauthorized", 401)
        assert error.status_code == 401
        assert "Unauthorized (status 401)" in str(error)

    def test_init_with_403(self) -> None:
        """Test initialization with 403 status code."""
        error = JevAuthError("Forbidden", 403)
        assert error.status_code == 403
        assert "Forbidden (status 403)" in str(error)

    def test_init_raises_with_invalid_status(self) -> None:
        """Test that initialization raises ValueError for invalid status."""
        with pytest.raises(ValueError, match="JevAuthError status code must be"):
            JevAuthError("Error", 404)


class TestJevRequestError:
    """Tests for JevRequestError."""

    def test_init_with_400(self) -> None:
        """Test initialization with 400 status code."""
        error = JevRequestError("Bad Request", 400)
        assert error.status_code == 400

    def test_init_with_404(self) -> None:
        """Test initialization with 404 status code."""
        error = JevRequestError("Not Found", 404)
        assert error.status_code == 404

    def test_init_raises_with_401(self) -> None:
        """Test that 401 raises ValueError (should be JevAuthError)."""
        with pytest.raises(ValueError, match="JevRequestError status code must be"):
            JevRequestError("Error", 401)

    def test_init_raises_with_403(self) -> None:
        """Test that 403 raises ValueError (should be JevAuthError)."""
        with pytest.raises(ValueError, match="JevRequestError status code must be"):
            JevRequestError("Error", 403)

    def test_init_raises_with_500(self) -> None:
        """Test that 500 raises ValueError (should be JevServiceError)."""
        with pytest.raises(ValueError, match="JevRequestError status code must be"):
            JevRequestError("Error", 500)

    def test_init_raises_with_200(self) -> None:
        """Test that 200 raises ValueError (should be JevResponseError)."""
        with pytest.raises(ValueError, match="JevRequestError status code must be"):
            JevRequestError("Error", 200)


class TestJevServiceError:
    """Tests for JevServiceError."""

    def test_init_with_500(self) -> None:
        """Test initialization with 500 status code."""
        error = JevServiceError("Internal Server Error", 500)
        assert error.status_code == 500

    def test_init_with_503(self) -> None:
        """Test initialization with 503 status code."""
        error = JevServiceError("Service Unavailable", 503)
        assert error.status_code == 503

    def test_init_with_none_for_transport_error(self) -> None:
        """Test initialization with None for transport errors."""
        error = JevServiceError("Connection timeout", None)
        assert error.status_code is None

    def test_init_raises_with_400(self) -> None:
        """Test that 400 raises ValueError (should be JevRequestError)."""
        with pytest.raises(ValueError, match="JevServiceError status code must be"):
            JevServiceError("Error", 400)

    def test_init_raises_with_200(self) -> None:
        """Test that 200 raises ValueError (should be JevResponseError)."""
        with pytest.raises(ValueError, match="JevServiceError status code must be"):
            JevServiceError("Error", 200)


class TestJevResponseError:
    """Tests for JevResponseError."""

    def test_init_with_200(self) -> None:
        """Test initialization with 200 status code."""
        error = JevResponseError("Parse error", 200)
        assert error.status_code == 200

    def test_init_with_201(self) -> None:
        """Test initialization with 201 status code."""
        error = JevResponseError("Parse error", 201)
        assert error.status_code == 201

    def test_init_raises_with_299(self) -> None:
        """Test initialization with 299 status code."""
        error = JevResponseError("Parse error", 299)
        assert error.status_code == 299

    def test_init_raises_with_300(self) -> None:
        """Test that 300 raises ValueError (not 2xx)."""
        with pytest.raises(ValueError, match="JevResponseError status code must be"):
            JevResponseError("Error", 300)

    def test_init_raises_with_400(self) -> None:
        """Test that 400 raises ValueError (should be JevRequestError)."""
        with pytest.raises(ValueError, match="JevResponseError status code must be"):
            JevResponseError("Error", 400)


class TestExceptionInheritance:
    """Tests for exception inheritance."""

    def test_jev_error_is_exception(self) -> None:
        """Test that JevError is an Exception."""
        assert issubclass(JevError, Exception)

    def test_jev_auth_error_is_jev_error(self) -> None:
        """Test that JevAuthError inherits from JevError."""
        assert issubclass(JevAuthError, JevError)

    def test_jev_request_error_is_jev_error(self) -> None:
        """Test that JevRequestError inherits from JevError."""
        assert issubclass(JevRequestError, JevError)

    def test_jev_service_error_is_jev_error(self) -> None:
        """Test that JevServiceError inherits from JevError."""
        assert issubclass(JevServiceError, JevError)

    def test_jev_response_error_is_jev_error(self) -> None:
        """Test that JevResponseError inherits from JevError."""
        assert issubclass(JevResponseError, JevError)

    def test_can_catch_all_jev_errors(self) -> None:
        """Test that catching JevError catches all subclasses."""
        errors = [
            JevAuthError("auth", 401),
            JevRequestError("bad request", 400),
            JevServiceError("server error", 500),
            JevResponseError("parse error", 200),
        ]
        for error in errors:
            with pytest.raises(JevError):
                raise error
