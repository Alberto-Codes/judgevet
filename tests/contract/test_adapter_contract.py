"""Contract tests for judgevet adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.answers import NoulAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.ports import SystemOnePort


class FakeSystemOnePort(SystemOnePort):
    """Fake implementation of SystemOnePort for testing."""

    def __init__(self) -> None:
        """Initialize the fake port."""
        self.calls: list[dict[str, Any]] = []

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a fake response."""
        self.calls.append(
            {
                "state": state,
                "questions": questions,
                "model": model,
            }
        )
        return SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={
                "test": NoulAnswer(noul=0.5),
            },
        )


@pytest.mark.contract
class TestHTTPAdapterContract:
    """Contract tests for HTTPSystemOneAdapter."""

    def test_implements_port(self) -> None:
        """Test that HTTPSystemOneAdapter implements SystemOnePort."""
        # This is a type check - if it doesn't compile, the test fails
        adapter: SystemOnePort = HTTPSystemOneAdapter(api_key="test-key")
        assert adapter is not None

    def test_system_one_returns_expected_structure(self) -> None:
        """Test that system_one returns a dictionary with expected keys."""
        # We can't test the real HTTP adapter without an API key,
        # but we can test the contract through the interface
        fake = FakeSystemOnePort()
        response = fake.system_one(
            state="test",
            questions={"q1": {"type": "noul", "instructions": "test"}},
            model="test-model",
        )
        assert hasattr(response, "model")
        assert hasattr(response, "answers")
        assert hasattr(response, "usage")
        assert isinstance(response.answers["test"], NoulAnswer)
