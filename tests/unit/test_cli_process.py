"""Assert observable HTTP calls and process outcomes for the installed CLI.

Examples:
    ```python
    from tests.cli_process_support import SUCCESS

    assert SUCCESS["model"] == "jev-1.13.0"
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Installed command behavior.
"""

import asyncio
import json

import pytest

from tests.cli_process_support import CANARY, QUESTIONS, SUCCESS, invoke, serve

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize(
    "status,payload",
    [
        (401, {"detail": {"error_type": "authentication_error", "message": "Denied"}}),
        (
            422,
            {
                "detail": [
                    {"type": "missing", "loc": ["body", "questions"], "msg": "Required"}
                ]
            },
        ),
        (503, {"detail": "Unavailable"}),
        (200, {"model": "jev-1.13.0", "answers": "wrong"}),
    ],
)
def test_installed_http_failure(status: int, payload: dict, as_json: bool) -> None:
    """A real failed HTTP interaction must produce a failed process.

    Args:
        status: Controlled HTTP code.
        payload: Controlled error or malformed answer.
        as_json: Whether to request JSON diagnostics.
    """
    with serve(status, payload) as peer:
        code, stdout, stderr = asyncio.run(
            invoke(peer.url, "test", json.dumps(QUESTIONS), as_json)
        )
    assert len(peer.requests) == (3 if status == 503 else 1)
    assert peer.requests[0]["path"] == "/v1/systemone"
    assert stdout == ""
    assert CANARY not in stderr
    assert "Traceback" not in stderr
    assert json.loads(stderr)["error"] if as_json else stderr.startswith("Error:")
    assert code == 1


@pytest.mark.parametrize("as_json", [False, True])
def test_installed_mixed_success(as_json: bool) -> None:
    """A successful real HTTP interaction prints all three answer types.

    Args:
        as_json: Whether to request machine output.
    """
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = asyncio.run(
            invoke(peer.url, "test", json.dumps(QUESTIONS), as_json)
        )
    assert code == 0
    assert stderr == ""
    assert len(peer.requests) == 1
    observed = peer.requests[0]
    assert observed["path"] == "/v1/systemone"
    assert observed["auth"] == f"Bearer {CANARY}"
    assert observed["body"]["state"] == "test"
    assert observed["body"]["model"] == "jev-1.13.0"
    assert {k: v["type"] for k, v in observed["body"]["questions"].items()} == {
        name: question["type"] for name, question in QUESTIONS.items()
    }
    if as_json:
        answer = json.loads(stdout)
        assert answer["model"] == SUCCESS["model"]
        assert answer["usage"] == SUCCESS["usage"]
        for name, expected in SUCCESS["answers"].items():
            assert answer["answers"][name] == {"name": name, **expected}
    else:
        for expected in ("jev-1.13.0", "noul", "choice", "score", "0.42", "1.5"):
            assert expected in stdout


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize(
    "state,questions",
    [
        ("test", "{"),
        ("{", "{}"),
        ("test", '{"q":{"type":"unknown"}}'),
    ],
)
def test_local_failure_never_calls_peer(
    state: str, questions: str, as_json: bool
) -> None:
    """Malformed local input must fail before any request leaves the process.

    Args:
        state: State input.
        questions: Questions input.
        as_json: Whether to request machine diagnostics.
    """
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = asyncio.run(invoke(peer.url, state, questions, as_json))
    assert peer.requests == []
    assert stdout == ""
    assert CANARY not in stderr
    assert "Traceback" not in stderr
    assert json.loads(stderr)["error"] if as_json else stderr.startswith("Error:")
    assert code == 1
