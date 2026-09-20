"""Unit tests for HTTP adapter."""

from unittest.mock import MagicMock, patch

import pytest

from jev_client.adapters.outbound.http import HTTPSystemOneAdapter


class TestHTTPSystemOneAdapter:
    """Tests for HTTPSystemOneAdapter."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        adapter = HTTPSystemOneAdapter(api_key="test-key")
        assert adapter is not None

    def test_init_with_env_var(self) -> None:
        """Test initialization with API key from environment."""
        with patch.dict("os.environ", {"TYPESAFE_API_KEY": "env-key"}):
            adapter = HTTPSystemOneAdapter()
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
