"""Mock transports and hosted adapters for the offline kit run (#272).

`answer_questions` answers every question a request carries, by its declared
type, in the wire shape of contract fixture 4. The kit asks its own
questions, which the contract fixtures do not name, so the handler does not
replay a success body verbatim. `replay` returns one contract fixture's status
and body as-is.
Source: https://github.com/Alberto-Codes/judgevet/issues/272#issuecomment-5921672670.
Source: https://docs.typesafe.ai/api.md.

Examples:
    ```python
    import httpx

    from tests.unit.hosted_kit_support import answer_questions, sync_adapter

    adapter = sync_adapter(httpx.MockTransport(answer_questions))
    adapter.close()
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: The hosted adapters built here
    - [judgevet.testing.conformance][]: The source of `VALID_ANSWERS`
"""

import json
from typing import Any

import httpx

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.testing.conformance import VALID_ANSWERS
from tests.contract.fixtures import get_fixture_by_name

BASE_URL = "http://127.0.0.1:9"
"""A loopback base URL. `MockTransport` never opens a socket to it."""

API_KEY = "synthetic"
"""The synthetic key every adapter here carries."""

MIXED = get_fixture_by_name("mixed_success")
"""Contract fixture 4, the source of the success wire shape and usage."""


def _wire_answer(answer: Answer) -> dict[str, Any]:
    """Encode a typed answer in the wire shape of contract fixture 4.

    Args:
        answer: A typed answer from `VALID_ANSWERS`.

    Returns:
        The answer as fixture 4's body carries it.

    Raises:
        TypeError: If the answer type is unknown.
    """
    if isinstance(answer, NoulAnswer):
        return {"type": "noul", "noul": answer.noul}
    if isinstance(answer, ChoiceAnswer):
        return {
            "type": "choice",
            "choice": answer.choice,
            "confidence": answer.confidence,
            "probabilities": dict(answer.probabilities),
        }
    if isinstance(answer, ScoreAnswer):
        return {
            "type": "score",
            "score": answer.score,
            "confidence": answer.confidence,
            "legend": dict(answer.legend),
            "probabilities": dict(answer.probabilities),
        }
    raise TypeError(f"Unknown answer type {type(answer).__name__}.")


WIRE_BY_TYPE = {
    wire["type"]: wire
    for wire in (_wire_answer(answer) for answer in VALID_ANSWERS.values())
}
"""The wire answer for each question type, built from `VALID_ANSWERS`."""


def answer_questions(request: httpx.Request) -> httpx.Response:
    """Answer every question a request carries, by its declared type.

    Args:
        request: The request the adapter sent.

    Returns:
        A 200 response in fixture 4's wire shape, echoing the request model.
    """
    payload = json.loads(request.content)
    answers = {
        name: WIRE_BY_TYPE[question["type"]]
        for name, question in payload["questions"].items()
    }
    body = {
        "model": payload["model"],
        "usage": MIXED["body"]["usage"],
        "answers": answers,
    }
    return httpx.Response(200, json=body)


def replay(name: str) -> httpx.MockTransport:
    """Return a transport that replays one contract fixture's status and body.

    Args:
        name: The contract fixture name.

    Returns:
        A transport that answers every request with that fixture verbatim.
    """
    fixture = get_fixture_by_name(name)

    def handle(request: httpx.Request) -> httpx.Response:
        """Build a fresh copy of the fixture response for each request.

        Args:
            request: The request the adapter sent, which the replay ignores.

        Returns:
            The fixture's status and body.
        """
        return httpx.Response(fixture["status"], json=fixture["body"])

    return httpx.MockTransport(handle)


def sync_adapter(transport: httpx.MockTransport) -> HTTPSystemOneAdapter:
    """Build a sync hosted adapter over a mock transport.

    Args:
        transport: The mock transport.

    Returns:
        The adapter.
    """
    return HTTPSystemOneAdapter(api_key=API_KEY, base_url=BASE_URL, transport=transport)


def async_adapter(transport: httpx.MockTransport) -> AsyncHTTPSystemOneAdapter:
    """Build an async hosted adapter over a mock transport.

    Args:
        transport: The mock transport.

    Returns:
        The adapter.
    """
    return AsyncHTTPSystemOneAdapter(
        api_key=API_KEY, base_url=BASE_URL, transport=transport
    )
