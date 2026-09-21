"""Unit tests for HTTP adapter."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import (
    JevAuthError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)


class TestHTTPSystemOneAdapter:
    """Tests for HTTPSystemOneAdapter."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")
        assert adapter is not None

    def test_init_raises_without_key(self) -> None:
        """Test that initialization raises ValueError without API key."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="API key must be provided"),
        ):
            HTTPSystemOneAdapter()

    def test_close(self) -> None:
        """Test that close closes the HTTP client."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")
        adapter.close()  # Should not raise

    def test_context_manager(self) -> None:
        """Test context manager protocol."""
        with HTTPSystemOneAdapter(api_key="test-key") as adapter:
            assert adapter is not None

    def test_system_one_calls_endpoint(self) -> None:
        """Test that system_one makes a POST request to the correct endpoint."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "model": "jev-1.13.0",
                "answers": {},
                "usage": {"input_tokens": 10, "output_tokens": 0},
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            adapter.system_one(
                state="test",
                questions={"q": {"type": "noul"}},
                model="test-model",
            )

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[0][0] == "/v1/systemone"
            assert call_kwargs[1]["json"]["model"] == "test-model"

    def test_system_one_translates_401_to_jev_auth_error(self) -> None:
        """Test that 401 is translated to JevAuthError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError, match=r"Unauthorized.*status 401"):
                adapter.system_one(state="test", questions={})

    def test_system_one_translates_403_to_jev_auth_error(self) -> None:
        """Test that 403 is translated to JevAuthError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Forbidden",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError, match=r"Forbidden.*status 403"):
                adapter.system_one(state="test", questions={})

    def test_system_one_translates_400_to_jev_request_error(self) -> None:
        """Test that 400 is translated to JevRequestError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Bad Request",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError, match=r"Bad Request.*status 400"):
                adapter.system_one(state="test", questions={})

    def test_system_one_translates_500_to_jev_service_error(self) -> None:
        """Test that 500 is translated to JevServiceError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(
                JevServiceError, match=r"Internal Server Error.*status 500"
            ):
                adapter.system_one(state="test", questions={})

    def test_system_one_translates_request_error_to_jev_service_error(self) -> None:
        """Test that transport errors are translated to JevServiceError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_post.side_effect = httpx.RequestError(
                message="Connection timeout",
                request=MagicMock(),
            )

            with pytest.raises(JevServiceError, match="Connection timeout") as exc_info:
                adapter.system_one(state="test", questions={})

            assert exc_info.value.status_code is None

    def test_api_key_not_in_error_messages_401(self) -> None:
        """Test that API key does not appear in 401 error messages."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert error.status_code == 401

    def test_api_key_not_in_error_messages_403(self) -> None:
        """Test that API key does not appear in 403 error messages."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Forbidden",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevAuthError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert error.status_code == 403

    def test_api_key_not_in_error_messages_400(self) -> None:
        """Test that API key does not appear in 400 error messages."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Bad Request",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevRequestError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert error.status_code == 400

    def test_api_key_not_in_error_messages_500(self) -> None:
        """Test that API key does not appear in 500 error messages."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(JevServiceError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert error.status_code == 500

    def test_api_key_not_in_error_messages_transport_failure(self) -> None:
        """Test that API key does not appear in transport error messages."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_post.side_effect = httpx.RequestError(
                message="Connection timeout",
                request=MagicMock(),
            )

            with pytest.raises(JevServiceError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert exc_info.value.status_code is None

    def test_api_key_not_in_error_messages_unparseable_body(self) -> None:
        """Test that API key does not appear when response body does not parse."""
        fake_key = "FAKE-KEY-TEST-12345"
        adapter = HTTPSystemOneAdapter(api_key=fake_key)

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response

            with pytest.raises(JevResponseError) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert fake_key not in str(error)
            assert fake_key not in repr(error)
            assert error.status_code == 200

    def test_system_one_translates_429_to_jev_rate_limit_error(self) -> None:
        """Test that 429 is translated to JevRateLimitError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Rate limit exceeded",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(
                JevRateLimitError, match=r"Rate limit exceeded.*status 429"
            ) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert error.status_code == 429
            assert error.retryable is True

    def test_system_one_translates_529_to_jev_service_error(self) -> None:
        """Test that 529 is translated to JevServiceError."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")

        with patch.object(adapter._client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 529
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                message="Service overloaded",
                request=MagicMock(),
                response=mock_response,
            )
            mock_post.return_value = mock_response

            with pytest.raises(
                JevServiceError, match=r"Service overloaded.*status 529"
            ) as exc_info:
                adapter.system_one(state="test", questions={})

            error = exc_info.value
            assert error.status_code == 529
            assert error.retryable is True

    def test_system_one_translates_read_timeout_to_jev_service_error(self) -> None:
        """Test that a ReadTimeout is translated to JevServiceError."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out", request=request)

        adapter = HTTPSystemOneAdapter(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(JevServiceError) as exc_info:
            adapter.system_one(state="test", questions={})

        error = exc_info.value
        assert error.retryable is True
        assert error.status_code is None
        assert "read timed out" in str(error)

    def test_default_timeout_reaches_client(self) -> None:
        """Test that the default 30 s read / 5 s connect timeout reaches the client."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")
        assert adapter._client._timeout == httpx.Timeout(30.0, connect=5.0)

    def test_explicit_timeout_reaches_client(self) -> None:
        """Test that an explicit timeout_seconds reaches the client."""
        adapter = HTTPSystemOneAdapter(api_key="test-key", timeout_seconds=90.0)
        assert adapter._client._timeout == httpx.Timeout(90.0, connect=5.0)

    def test_init_raises_on_zero_timeout(self) -> None:
        """Test that a zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds"):
            HTTPSystemOneAdapter(api_key="test-key", timeout_seconds=0)

    def test_init_raises_on_negative_timeout(self) -> None:
        """Test that a negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds"):
            HTTPSystemOneAdapter(api_key="test-key", timeout_seconds=-1.0)
