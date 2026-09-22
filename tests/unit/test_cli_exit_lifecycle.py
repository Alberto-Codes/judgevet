"""Preserve integer helper contracts and adapter ownership at the CLI boundary.

Examples:
    ```python
    from judgevet.adapters.inbound.cli import main

    assert callable(main)
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Command composition and helpers.
"""

import sys
from collections.abc import Mapping
from typing import Any

import pytest

from judgevet.adapters.inbound import cli
from judgevet.domain.answers import NoulAnswer
from judgevet.domain.errors import JevServiceError
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage

pytestmark = pytest.mark.unit
QUESTIONS = '{"q":{"type":"noul","instructions":"True?"}}'


class RecordingPort:
    """Record calls and closure while providing a success or handled failure.

    Attributes:
        fail: Whether to raise a service error.
        calls: Number of judgment calls.
        closes: Number of adapter closures.
    """

    def __init__(self, fail: bool) -> None:
        """Initialize recorded effects.

        Args:
            fail: Whether the request should fail.
        """
        self.fail = fail
        self.calls = 0
        self.closes = 0

    def close(self) -> None:
        """Record adapter closure."""
        self.closes += 1

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a typed answer or the controlled service error.

        Args:
            state: Input state.
            questions: Typed questions.
            model: Selected model.

        Returns:
            Typed answer for the single test question.

        Raises:
            JevServiceError: When the fixture selects failure.
        """
        self.calls += 1
        if self.fail:
            raise JevServiceError("Controlled failure", 503)
        return SystemOneResponse(
            model=model,
            usage=Usage(input_tokens=1, output_tokens=1),
            answers={"q": NoulAnswer(noul=0.5)},
        )


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("entry", ["run_cli", "main", "cli_main"])
def test_integer_helpers_and_cleanup(
    fail: bool,
    entry: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Helper calls return integers and composition roots close exactly once.

    Args:
        fail: Whether to exercise a handled service failure.
        entry: Public helper under test.
        monkeypatch: Isolate construction and legacy arguments.
    """
    port = RecordingPort(fail)

    def factory(**kwargs: object) -> RecordingPort:
        """Provide the recording adapter.

        Args:
            kwargs: Production constructor arguments.

        Returns:
            The same recording adapter for effect inspection.
        """
        return port

    monkeypatch.setattr(cli, "HTTPSystemOneAdapter", factory)
    monkeypatch.setenv("JEV_API__KEY", "offline-cli-canary")
    if entry == "run_cli":
        code = cli.run_cli(port, "test", QUESTIONS, "jev-1.13.0", True)
    elif entry == "main":
        code = cli.main("test", QUESTIONS, "jev-1.13.0", None, True)
    else:
        monkeypatch.setattr(sys, "argv", ["judgevet", "test", QUESTIONS, "--json"])
        code = cli.cli_main()
    assert type(code) is int
    assert code == int(fail)
    assert port.calls == 1
    assert port.closes == (0 if entry == "run_cli" else 1)
