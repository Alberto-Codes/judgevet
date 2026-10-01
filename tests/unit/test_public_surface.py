"""Pin what ``import judgevet`` exposes.

The package root is the public API. Everything else is a module path a
caller should not have to know, and this suite exists because the async
adapter shipped in #92 without being reachable from the root: a user could
`from judgevet import HTTPSystemOneAdapter` but had to reach into
`judgevet.adapters.outbound.http` for the async one.

A name leaving ``__all__`` is a breaking change for anyone importing it, so
the set is asserted whole rather than checked one membership at a time — an
accidental removal fails here with the diff, not at a user's import.
"""

from __future__ import annotations

import pytest

import judgevet
from judgevet import AsyncHTTPSystemOneAdapter, HTTPSystemOneAdapter, ports
from judgevet.domain import answers, audit, errors, questions, response, usage
from judgevet.testing import conformance

EXPECTED_EXPORTS = {
    "Answer",
    "AsyncSystemOnePort",
    "AuditSink",
    "ChoiceAnswer",
    "JevAuthError",
    "JevBudgetExceededError",
    "JevError",
    "JevMaxTokensExceededError",
    "JevRateLimitError",
    "JevRequestError",
    "JevResponseError",
    "JevServiceError",
    "JudgevetError",
    "JudgmentRecord",
    "NoulAnswer",
    "Question",
    "RetryPolicy",
    "ScoreAnswer",
    "SpendCap",
    "StateRedactor",
    "SystemOnePort",
    "SystemOneResponse",
    "Usage",
    "AsyncHTTPSystemOneAdapter",
    "Choice",
    "HTTPSystemOneAdapter",
    "NetworkConfig",
    "GatewayConfig",
    "RequestMetadata",
    "Noul",
    "Score",
    "VERIFIED_MODEL",
    "__version__",
    "bind_request_id",
}

EXPECTED_CONFORMANCE_EXPORTS = (
    "CONFORMANCE_MODEL",
    "CONFORMANCE_POLICY",
    "CONFORMANCE_QUESTIONS",
    "CONFORMANCE_STATE",
    "INVALID_ANSWERS",
    "VALID_ANSWERS",
    "AsyncProviderFactory",
    "BaseAsyncProviderConformance",
    "BaseProviderConformance",
)


def test_all_matches_the_documented_surface() -> None:
    """``__all__`` is exactly the set this project promises."""
    assert set(judgevet.__all__) == EXPECTED_EXPORTS


def test_every_exported_name_actually_resolves() -> None:
    """Every name in ``__all__`` is importable from the root.

    A name listed but not bound raises at ``from judgevet import X`` for the
    caller and nowhere else, so it is checked here instead.
    """
    missing = [name for name in judgevet.__all__ if not hasattr(judgevet, name)]
    assert not missing, f"listed in __all__ but not bound: {missing}"


def test_both_adapters_are_reachable_from_the_root() -> None:
    """The sync and async adapters are equally public.

    This is the regression #92 shipped with: the async adapter existed and
    was proven equivalent, but only the sync one was importable from the
    package root.

    The module-level import at the top of this file is itself half the
    assertion: if either name left the root, this file would fail to import
    and every test in it would error.
    """
    assert HTTPSystemOneAdapter.__name__ == "HTTPSystemOneAdapter"
    assert AsyncHTTPSystemOneAdapter.__name__ == "AsyncHTTPSystemOneAdapter"


def test_the_async_adapter_refuses_the_sync_lifecycle() -> None:
    """``close``/``__enter__``/``__exit__`` are absent on purpose.

    A synchronous ``close()`` would call ``aclose()`` without awaiting it,
    return an un-awaited coroutine and close nothing. An ``AttributeError``
    is the louder failure, and the docstring promises it.
    """
    adapter = AsyncHTTPSystemOneAdapter(api_key="test-key")
    absent = [n for n in ("close", "__enter__", "__exit__") if hasattr(adapter, n)]
    assert not absent, f"async adapter should not expose: {absent}"
    assert hasattr(adapter, "aclose")
    assert hasattr(adapter, "__aenter__")


@pytest.mark.parametrize(
    "name,original",
    [
        ("StateRedactor", ports.StateRedactor),
        ("AuditSink", ports.AuditSink),
        ("JudgmentRecord", audit.JudgmentRecord),
        ("SystemOnePort", ports.SystemOnePort),
        ("AsyncSystemOnePort", ports.AsyncSystemOnePort),
        ("Question", questions.Question),
        ("Answer", answers.Answer),
        ("NoulAnswer", answers.NoulAnswer),
        ("ChoiceAnswer", answers.ChoiceAnswer),
        ("ScoreAnswer", answers.ScoreAnswer),
        ("SystemOneResponse", response.SystemOneResponse),
        ("Usage", usage.Usage),
        ("JevError", errors.JevError),
        ("JudgevetError", errors.JudgevetError),
        ("JevAuthError", errors.JevAuthError),
        ("JevBudgetExceededError", errors.JevBudgetExceededError),
        ("JevRequestError", errors.JevRequestError),
        ("JevMaxTokensExceededError", errors.JevMaxTokensExceededError),
        ("JevResponseError", errors.JevResponseError),
        ("JevServiceError", errors.JevServiceError),
        ("JevRateLimitError", errors.JevRateLimitError),
        ("Noul", questions.Noul),
        ("Choice", questions.Choice),
        ("Score", questions.Score),
    ],
)
def test_exports_preserve_deep_import_identity(name: str, original: object) -> None:
    """Root exports retain the original objects and existing deep imports."""
    assert getattr(judgevet, name) is original


def test_conformance_kit_exports_its_documented_surface() -> None:
    """The conformance kit exports exactly its promised names, all bound.

    A provider test suite imports these names, so a removal breaks it.
    `AsyncProviderFactory` is pinned here so async provider suites never
    reach into the private `_conformance_async` module (#277).
    """
    assert sorted(conformance.__all__) == sorted(EXPECTED_CONFORMANCE_EXPORTS)
    for name in EXPECTED_CONFORMANCE_EXPORTS:
        assert getattr(conformance, name) is not None
