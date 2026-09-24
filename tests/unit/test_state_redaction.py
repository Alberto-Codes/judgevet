"""Observe caller-controlled redaction at real loopback HTTP boundaries."""

import copy

import pytest

from judgevet import GatewayConfig, bind_request_id
from judgevet.domain.errors import JevServiceError
from tests.gateway_support import gateway_peer, observed_headers
from tests.redaction_support import State, SyntheticRedactor, invoke

STATES: list[State] = [
    "state-canary",
    {"record": {"content": "state-canary"}, "items": ["state-canary", {"keep": 1}]},
    ["state-canary", {"content": "state-canary"}],
]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("gateway_enabled", [False, True])
@pytest.mark.parametrize("state", STATES)
def test_only_transformed_state_reaches_gateway(
    asynchronous, gateway_enabled, state
) -> None:
    """The gateway receives transformed state while the caller retains its input."""
    original = copy.deepcopy(state)
    redactor = SyntheticRedactor()
    gateway = (
        GatewayConfig(
            auth_header="x-apikey",
            auth_scheme="",
            headers={"Example-Tenant": "synthetic"},
            request_id_header="Example-Request",
        )
        if gateway_enabled
        else None
    )
    with gateway_peer() as peer, bind_request_id("redaction-call"):
        invoke(asynchronous, redactor, state, url=peer.url + "/prefix", gateway=gateway)
    assert state == original
    assert redactor.calls == 1
    path, _, payload = peer.requests[0]
    assert path == "/prefix/v1/systemone"
    assert "state-canary" not in str(payload)
    assert payload == {
        "state": redactor.output,
        "questions": {"q": {"type": "noul", "instructions": "question-canary"}},
        "model": "jev-1.13.0",
    }
    headers = observed_headers(peer)
    assert headers["example-explicit"] == "header-canary"
    assert headers["x-apikey" if gateway_enabled else "authorization"] == (
        "dummy" if gateway_enabled else "Bearer dummy"
    )
    if gateway_enabled:
        assert headers["example-tenant"] == "synthetic"
        assert headers["example-request"] == "redaction-call"


class FailingRedactor:
    """Mutate a private nested copy before raising a retryable failure."""

    def __init__(self) -> None:
        """Keep an identifiable exception to prove propagation without fallback."""
        self.calls = 0
        self.error = JevServiceError("synthetic callback failure", 503)

    def redact(self, state: State) -> State:
        """Mutate a nested field and stop before serialization."""
        self.calls += 1
        assert isinstance(state, dict)
        state["nested"]["content"] = "changed"
        raise self.error


@pytest.mark.parametrize("asynchronous", [False, True])
def test_redactor_failure_prevents_every_request(asynchronous) -> None:
    """Retryable callback errors neither transmit nor mutate caller data."""
    state = {"nested": {"content": "state-canary"}}
    redactor = FailingRedactor()
    with gateway_peer() as peer:
        with pytest.raises(JevServiceError) as caught:
            invoke(asynchronous, redactor, state, url=peer.url)
        assert peer.requests == []
    assert caught.value is redactor.error
    assert state == {"nested": {"content": "state-canary"}}
    assert redactor.calls == 1


class InvalidJSONRedactor:
    """Return a typed container with a deliberately non-JSON nested object."""

    def __init__(self, output: State) -> None:
        """Keep deliberately invalid nested data and count invocations."""
        self.calls = 0
        self.output = output

    def redact(self, state: State) -> State:
        """Supply invalid output to exercise serialization failure before IO."""
        self.calls += 1
        return self.output


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "output,error",
    [
        ({"invalid": object()}, TypeError),
        ({"invalid": float("nan")}, ValueError),
        ({"invalid": float("inf")}, ValueError),
    ],
)
def test_invalid_redactor_output_prevents_transmission(
    asynchronous, output, error
) -> None:
    """Never fall back to original state when output cannot be serialized."""
    redactor = InvalidJSONRedactor(output)
    with gateway_peer() as peer:
        with pytest.raises(error):
            invoke(asynchronous, redactor, "state-canary", url=peer.url)
        assert peer.requests == []

    assert redactor.calls == 1


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("state", STATES)
def test_none_redactor_retains_payload(asynchronous, state) -> None:
    """Explicit None preserves state, questions, model and authentication."""
    with gateway_peer() as peer:
        invoke(asynchronous, None, state, url=peer.url)
    assert peer.requests[0][2] == {
        "state": state,
        "questions": {"q": {"type": "noul", "instructions": "question-canary"}},
        "model": "jev-1.13.0",
    }
    assert observed_headers(peer)["authorization"] == "Bearer dummy"
