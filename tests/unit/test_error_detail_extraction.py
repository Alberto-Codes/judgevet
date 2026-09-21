"""Unit tests for error detail extraction in HTTP adapter."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import (
    JevAuthError,
    JevRequestError,
    JevServiceError,
)


class TestErrorDetailExtraction:
    """Tests for error detail extraction from API responses."""

    def test_422_detail_array_shows_field_location(self) -> None:
        """Test that 422 with array detail shows type, loc, and msg."""
        sentinel = "S3N71N3L-7357-422-DE73CT1ON"
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "questions"],
                    "msg": "Field required",
                    "input": {"state": sentinel, "model": "jev-latest"},
                }
            ]
        }

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unprocessable Entity",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            # Should include field location info
            assert "missing" in str(error)
            assert "body.questions" in str(error)
            assert "Field required" in str(error)
            # Should NOT include input (caller content)
            assert sentinel not in str(error)
            assert sentinel not in repr(error)
            assert error.status_code == 422
            assert error.retryable is False

    def test_401_detail_object_shows_error_type_and_message(self) -> None:
        """Test that 401 with object detail shows error_type and message."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {
            "detail": {
                "error_type": "authentication_error",
                "message": "Cannot authenticate with the server...",
            }
        }

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert "authentication_error" in str(error)
            assert "Cannot authenticate with the server..." in str(error)
            assert error.status_code == 401
            assert error.retryable is False

    def test_error_without_detail_field(self) -> None:
        """Test that errors without detail field still work."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "bad request"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Bad Request",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            # Should still have the default error message
            assert "Bad Request" in str(error)
            assert error.status_code == 400

    def test_error_with_empty_detail(self) -> None:
        """Test that errors with empty detail work."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_response.json.return_value = {"detail": []}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unprocessable Entity",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert error.status_code == 422

    def test_422_detail_multiple_errors(self) -> None:
        """Test that multiple validation errors are all shown."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "state"],
                    "msg": "Field required",
                },
                {
                    "type": "missing",
                    "loc": ["body", "questions"],
                    "msg": "Field required",
                },
            ]
        }

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unprocessable Entity",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            # Both errors should be in the message
            assert "state" in str(error)
            assert "questions" in str(error)

    def test_401_detail_only_message(self) -> None:
        """Test 401 detail with only message field."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {"detail": {"message": "Invalid token format"}}

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert "Invalid token format" in str(error)

    def test_401_detail_only_error_type(self) -> None:
        """Test 401 detail with only error_type field."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {"detail": {"error_type": "expired_token"}}

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert "expired_token" in str(error)

    def test_422_detail_with_loc_as_numbers(self) -> None:
        """Test that loc with numeric indices is handled."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        mock_body = {
            "detail": [
                {
                    "type": "invalid",
                    "loc": ["body", 0, "field"],
                    "msg": "Invalid value",
                }
            ]
        }

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_response.json.return_value = mock_body
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unprocessable Entity",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert "body.0.field" in str(error)

    def test_non_json_error_body(self) -> None:
        """Test that non-JSON error bodies fall back gracefully."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevServiceError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            # Should have the default error message from str(exc)
            assert "Internal Server Error" in str(error)
