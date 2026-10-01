"""Acceptance tests for the provider conformance kit in judgevet.testing (#241).

judgevet's own offline fakes must pass every rule. Each deliberately broken
fake must fail exactly the rule it breaks and pass every other rule, shown
through pytester subprocess runs. Source:
https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.
"""

from __future__ import annotations

import re
import sys
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager, nullcontext
from dataclasses import replace
from textwrap import dedent, indent
from typing import Any

import pytest

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.media import ImageEvidence, MediaCapabilities
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.media import judge_with_images
from judgevet.policy import PolicyAnswerError, evaluate_policy
from judgevet.ports import AsyncSystemOnePort
from judgevet.providers import (
    AsyncProviderFactory,
    ProviderFactory,
    ProviderTransportError,
)
from judgevet.testing import (
    AsyncFakeSystemOnePort,
    FakeSystemOnePort,
    _conformance_async_scope,
)
from judgevet.testing._conformance_probes import BodyError, declared_evidence
from judgevet.testing.conformance import (
    CONFORMANCE_POLICY,
    CONFORMANCE_QUESTIONS,
    CONFORMANCE_STATE,
    INVALID_ANSWERS,
    VALID_ANSWERS,
    BaseAsyncProviderConformance,
    BaseProviderConformance,
)
from tests.fixtures.providers.provider_fixture import RecordingProvider, drain, owned

pytest_plugins = ["pytester"]

SCOPE_TESTS = (
    "test_scope_entry_yields_usable_port",
    "test_scope_exit_runs_once",
    "test_scope_propagates_body_exception",
)
RULE_TESTS = (
    "test_port_shape",
    "test_typed_answers_pass_policy",
    "test_failure_raises_provider_error",
    *SCOPE_TESTS,
    "test_media_refused_without_media_support",
    "test_media_port_refuses_undeclared_media",
    "test_media_port_judges_declared_media",
)
MEDIA_PORT_TESTS = RULE_TESTS[-2:]
ASYNC_RULE_TESTS = RULE_TESTS[:6]


class TestApplicationFixtureConformance(BaseProviderConformance):
    """The application-owned provider fixture passes every rule in process."""

    @pytest.fixture
    def provider_factory(self) -> Iterator[ProviderFactory]:
        """Own a recording provider per scope, then clear its events."""
        yield lambda: owned("conformance-owned")
        drain()

    @pytest.fixture
    def provider_port(self) -> FakeSystemOnePort:
        """Answer the kit questions with the kit's valid answers."""
        return FakeSystemOnePort(answers=VALID_ANSWERS)

    @pytest.fixture
    def failing_port(self) -> Iterator[RecordingProvider]:
        """Raise a transport failure from every judgment."""
        yield RecordingProvider("conformance-failing", fail=True)
        drain()

    @pytest.fixture
    def media_port(self) -> Iterator[RecordingProvider]:
        """Declare PNG and JPEG support only."""
        yield _KitRecordingProvider("conformance-media")
        drain()


class _KitRecordingProvider(RecordingProvider):
    """The recording fixture provider, answering media calls with kit answers."""

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Record the media call, then answer the kit questions."""
        recorded = super().system_one_media(state, questions, model, evidence=evidence)
        return replace(recorded, answers=dict(VALID_ANSWERS))


class _MediaFake(FakeSystemOnePort):
    """A public fake that also declares image support and judges media as text."""

    declared = MediaCapabilities({"image/png"})

    def capabilities(self, model: str) -> MediaCapabilities:
        """Declare the same image support for every model."""
        return self.declared

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Answer as the text fake does."""
        return self.system_one(state, questions, model)


class TestMediaCapableFakeConformance(BaseProviderConformance):
    """A media-capable port from the default port fixture serves both media rules."""

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Borrow a scripted media-capable fake per scope."""
        return lambda: nullcontext(_MediaFake(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self) -> FakeSystemOnePort:
        """Raise a declared provider failure from every judgment."""
        return FakeSystemOnePort(error=ProviderTransportError("synthetic failure"))


class TestAsyncFakeConformance(BaseAsyncProviderConformance):
    """The public async fake passes every async rule in process."""

    @pytest.fixture
    def provider_factory(self) -> Any:
        """Borrow a scripted async fake per scope."""
        return lambda: nullcontext(AsyncFakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self) -> AsyncFakeSystemOnePort:
        """Raise a declared provider failure from every judgment."""
        return AsyncFakeSystemOnePort(error=ProviderTransportError("synthetic"))


@pytest.mark.unit
def test_kit_questions_cover_every_kind() -> None:
    """The kit asks one Noul, one Choice and one Score question."""
    kinds = sorted(
        type(question).__name__ for question in CONFORMANCE_QUESTIONS.values()
    )
    assert kinds == ["Choice", "Noul", "Score"]
    assert isinstance(CONFORMANCE_STATE, str)


@pytest.mark.unit
def test_valid_answers_are_typed_and_accepted() -> None:
    """The valid answers match each question kind and pass the kit policy."""
    expected: dict[type, type] = {
        Noul: NoulAnswer,
        Choice: ChoiceAnswer,
        Score: ScoreAnswer,
    }
    for name, question in CONFORMANCE_QUESTIONS.items():
        assert isinstance(VALID_ANSWERS[name], expected[type(question)])
    assert evaluate_policy(CONFORMANCE_POLICY, VALID_ANSWERS).passed


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(INVALID_ANSWERS))
def test_invalid_answers_are_rejected(case: str) -> None:
    """Every invalid answer set is refused by the public policy evaluator."""
    assert set(INVALID_ANSWERS[case]) == set(CONFORMANCE_QUESTIONS)
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(CONFORMANCE_POLICY, INVALID_ANSWERS[case])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("media_type", "signature"),
    [
        ("image/png", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", b"\xff\xd8\xff"),
        ("image/webp", b"RIFF"),
    ],
)
def test_declared_evidence_is_judged_by_the_media_fake(
    media_type: str, signature: bytes
) -> None:
    """Kit evidence for each declared type passes judge_with_images and the policy."""
    declared = MediaCapabilities({media_type})
    evidence = declared_evidence(declared)
    assert evidence is not None
    (image,) = evidence.images
    assert image.media_type == media_type
    assert image.data.startswith(signature)
    assert set(evidence.by_question) <= set(CONFORMANCE_QUESTIONS)
    port = _MediaFake(answers=VALID_ANSWERS)
    port.declared = declared
    response = judge_with_images(
        port, CONFORMANCE_STATE, CONFORMANCE_QUESTIONS, "m", evidence=evidence
    )
    assert evaluate_policy(CONFORMANCE_POLICY, response.answers).passed


@pytest.mark.unit
@pytest.mark.parametrize(
    "capabilities",
    [
        MediaCapabilities({"image/gif"}),
        MediaCapabilities({"image/png", "image/jpeg", "image/webp"}, max_image_bytes=8),
        MediaCapabilities({"image/png"}, max_total_bytes=8),
    ],
    ids=["unsupported-type", "image-ceiling", "total-ceiling"],
)
def test_declared_evidence_is_none_when_nothing_fits(
    capabilities: MediaCapabilities,
) -> None:
    """No kit image is built when the declaration admits none of them."""
    assert declared_evidence(capabilities) is None


@pytest.mark.unit
def test_testing_package_does_not_import_pytest(pytester: pytest.Pytester) -> None:
    """The fakes package imports in a fresh interpreter without loading pytest."""
    result = pytester.run(
        sys.executable,
        "-c",
        "import sys, judgevet.testing; "
        "print(judgevet.testing.FakeSystemOnePort.__name__, 'pytest' in sys.modules)",
    )
    assert result.ret == 0, result.stderr.str()
    assert result.outlines == ["FakeSystemOnePort False"]


@pytest.mark.unit
def test_kit_without_pytest_names_the_extra(pytester: pytest.Pytester) -> None:
    """Importing the kit where pytest is absent raises an ImportError naming the extra."""
    result = pytester.run(
        sys.executable,
        "-c",
        "import sys\n"
        "sys.modules['pytest'] = None\n"
        "try:\n"
        "    import judgevet.testing.conformance\n"
        "except ImportError as error:\n"
        "    print(type(error).__name__, error)\n",
    )
    assert result.ret == 0, result.stderr.str()
    assert result.outlines[0].startswith("ImportError ")
    assert "judgevet[conformance]" in result.outlines[0]


@pytest.mark.unit
def test_async_kit_without_pytest_names_the_extra(pytester: pytest.Pytester) -> None:
    """Importing the async kit class where pytest is absent names the extra."""
    result = pytester.run(
        sys.executable,
        "-c",
        "import sys\n"
        "sys.modules['pytest'] = None\n"
        "try:\n"
        "    from judgevet.testing.conformance import BaseAsyncProviderConformance\n"
        "except ImportError as error:\n"
        "    print(type(error).__name__, error)\n",
    )
    assert result.ret == 0, result.stderr.str()
    assert result.outlines[0].startswith("ImportError ")
    assert "judgevet[conformance]" in result.outlines[0]


_GOOD = """\
from contextlib import nullcontext

import pytest

from judgevet.domain.media import MediaCapabilities
from judgevet.providers import ProviderTransportError
from judgevet.testing import FakeSystemOnePort
from judgevet.testing.conformance import (
    INVALID_ANSWERS,
    VALID_ANSWERS,
    BaseProviderConformance,
)


class MediaFake(FakeSystemOnePort):
    def capabilities(self, model):
        return MediaCapabilities({"image/png"})

    def system_one_media(self, state, questions, model, *, evidence):
        return self.system_one(state, questions, model)


class GoodProvider(BaseProviderConformance):
    @pytest.fixture
    def provider_factory(self):
        return lambda: nullcontext(FakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self):
        return FakeSystemOnePort(error=ProviderTransportError("synthetic"))

    @pytest.fixture
    def media_port(self):
        return MediaFake(answers=VALID_ANSWERS)


class ValidPortProvider(GoodProvider):
    @pytest.fixture
    def provider_port(self):
        return FakeSystemOnePort(answers=VALID_ANSWERS)


class Context:
    def __init__(self):
        self.port = FakeSystemOnePort(answers=VALID_ANSWERS)

    def __enter__(self):
        return self.port

    def __exit__(self, *exc_info):
        return None


class SwallowingContext(Context):
    def __exit__(self, *exc_info):
        return True


SHARED = Context()


class KeywordModelPort:
    def __init__(self):
        self.inner = FakeSystemOnePort(answers=VALID_ANSWERS)

    def system_one(self, state, questions, *, model):
        return self.inner.system_one(state, questions, model)


class ReturningPort:
    def system_one(self, state, questions, model):
        return FakeSystemOnePort(answers=VALID_ANSWERS).system_one(
            state, questions, model
        )


class SetCapabilitiesFake(MediaFake):
    def capabilities(self, model):
        return {"image/png"}


class CapabilitiesOnlyPort(FakeSystemOnePort):
    def capabilities(self, model):
        return MediaCapabilities({"image/png"})


class NonCallableCapabilitiesPort(MediaFake):
    capabilities = None


class RaisingMediaFake(MediaFake):
    def system_one_media(self, state, questions, model, *, evidence):
        raise RuntimeError("media backend exploded")
"""

_BROKEN = {
    "keyword_only_model": (
        "GoodProvider",
        "provider_port",
        "KeywordModelPort()",
        ("test_port_shape",),
    ),
    "wrong_answer_type": (
        "GoodProvider",
        "provider_port",
        'FakeSystemOnePort(answers=INVALID_ANSWERS["noul_for_choice"])',
        ("test_typed_answers_pass_policy",),
    ),
    "policy_rejects_score": (
        "GoodProvider",
        "provider_port",
        'FakeSystemOnePort(answers=INVALID_ANSWERS["score_off_scale"])',
        ("test_typed_answers_pass_policy",),
    ),
    "bare_runtime_error": (
        "GoodProvider",
        "failing_port",
        'FakeSystemOnePort(error=RuntimeError("boom"))',
        ("test_failure_raises_provider_error",),
    ),
    "failing_port_returns": (
        "GoodProvider",
        "failing_port",
        "ReturningPort()",
        ("test_failure_raises_provider_error",),
    ),
    "factory_yields_invalid_port": (
        "ValidPortProvider",
        "provider_factory",
        "lambda: nullcontext(object())",
        SCOPE_TESTS,
    ),
    "shared_context_exits_twice": (
        "GoodProvider",
        "provider_factory",
        "lambda: SHARED",
        ("test_scope_exit_runs_once",),
    ),
    "context_swallows_body_error": (
        "GoodProvider",
        "provider_factory",
        "SwallowingContext",
        ("test_scope_propagates_body_exception",),
    ),
    "text_port_claimed_as_media": (
        "GoodProvider",
        "media_port",
        "FakeSystemOnePort(answers=VALID_ANSWERS)",
        MEDIA_PORT_TESTS,
    ),
    "capabilities_without_media_method": (
        "GoodProvider",
        "provider_port",
        "CapabilitiesOnlyPort(answers=VALID_ANSWERS)",
        ("test_media_refused_without_media_support",),
    ),
    "non_callable_capabilities": (
        "GoodProvider",
        "provider_port",
        "NonCallableCapabilitiesPort(answers=VALID_ANSWERS)",
        ("test_media_refused_without_media_support",),
    ),
    "undeclared_capabilities": (
        "GoodProvider",
        "media_port",
        "SetCapabilitiesFake(answers=VALID_ANSWERS)",
        MEDIA_PORT_TESTS,
    ),
    "media_method_raises_runtime_error": (
        "GoodProvider",
        "media_port",
        "RaisingMediaFake(answers=VALID_ANSWERS)",
        ("test_media_port_judges_declared_media",),
    ),
    "media_policy_rejects_score": (
        "GoodProvider",
        "media_port",
        'MediaFake(answers=INVALID_ANSWERS["score_off_scale"])',
        ("test_media_port_judges_declared_media",),
    ),
}

_OUTCOME = re.compile(r"::(test_\w+) (PASSED|FAILED|ERROR|SKIPPED)")


def _run_output(pytester: pytest.Pytester, body: str) -> tuple[dict[str, str], str]:
    """Run one provider module in a pytest subprocess; return outcomes and output."""
    pytester.makepyfile(test_provider=_GOOD + "\n\n" + body)
    result = pytester.runpytest_subprocess("-v", "-p", "no:cacheprovider")
    output = result.stdout.str()
    outcomes = dict(_OUTCOME.findall(output))
    assert set(outcomes) == set(RULE_TESTS), output
    return outcomes, output


def _run(pytester: pytest.Pytester, body: str) -> dict[str, str]:
    """Run one provider module in a pytest subprocess and map test to outcome."""
    return _run_output(pytester, body)[0]


@pytest.mark.unit
def test_good_provider_passes_every_rule(pytester: pytest.Pytester) -> None:
    """A correct provider passes all nine rule tests."""
    outcomes = _run(pytester, "class TestGood(GoodProvider):\n    pass\n")
    assert outcomes == dict.fromkeys(RULE_TESTS, "PASSED")


@pytest.mark.unit
def test_provider_without_media_port_skips_only_media_port_rule(
    pytester: pytest.Pytester,
) -> None:
    """A provider with no media port skips the media-port rules and passes the rest."""
    body = dedent(
        """\
        class TestTextOnly(GoodProvider):
            @pytest.fixture
            def media_port(self):
                return None
        """
    )
    outcomes = _run(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected.update(dict.fromkeys(MEDIA_PORT_TESTS, "SKIPPED"))
    assert outcomes == expected


@pytest.mark.unit
def test_media_capable_provider_port_skips_text_only_rule(
    pytester: pytest.Pytester,
) -> None:
    """A media-capable provider port skips the text-only rule; the media rule runs."""
    body = dedent(
        """\
        class TestMediaPort(GoodProvider):
            @pytest.fixture
            def provider_port(self):
                return MediaFake(answers=VALID_ANSWERS)
        """
    )
    outcomes = _run(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected["test_media_refused_without_media_support"] = "SKIPPED"
    assert outcomes == expected


@pytest.mark.unit
def test_media_capable_fake_passes_declared_media_rule(
    pytester: pytest.Pytester,
) -> None:
    """The media-capable judgevet fake runs and passes the declared-media rule."""
    outcomes = _run(pytester, "class TestMedia(GoodProvider):\n    pass\n")
    assert outcomes["test_media_port_judges_declared_media"] == "PASSED"


@pytest.mark.unit
def test_media_port_without_kit_image_type_skips_declared_media_rule(
    pytester: pytest.Pytester,
) -> None:
    """A media port declaring no image type the kit can send skips that rule only."""
    body = dedent(
        """\
        class GifFake(MediaFake):
            def capabilities(self, model):
                return MediaCapabilities({"image/gif"})


        class TestGif(GoodProvider):
            @pytest.fixture
            def media_port(self):
                return GifFake(answers=VALID_ANSWERS)
        """
    )
    outcomes = _run(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected["test_media_port_judges_declared_media"] = "SKIPPED"
    assert outcomes == expected


@pytest.mark.unit
def test_media_runtime_error_names_the_provider_error_contract(
    pytester: pytest.Pytester,
) -> None:
    """A bare media failure fails the rule with a message naming ProviderError."""
    body = dedent(
        """\
        class TestRaising(GoodProvider):
            @pytest.fixture
            def media_port(self):
                return RaisingMediaFake(answers=VALID_ANSWERS)
        """
    )
    outcomes, output = _run_output(pytester, body)
    assert outcomes["test_media_port_judges_declared_media"] == "FAILED"
    assert "judgevet.providers.ProviderError" in output
    assert "RuntimeError" in output


@pytest.mark.unit
def test_media_provider_error_fails_declared_media_rule(
    pytester: pytest.Pytester,
) -> None:
    """A declared provider failure on declared media still fails the rule."""
    body = dedent(
        """\
        class FailingMediaFake(MediaFake):
            def system_one_media(self, state, questions, model, *, evidence):
                raise ProviderTransportError("media offline")


        class TestFailingMedia(GoodProvider):
            @pytest.fixture
            def media_port(self):
                return FailingMediaFake(answers=VALID_ANSWERS)
        """
    )
    outcomes, output = _run_output(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected["test_media_port_judges_declared_media"] = "FAILED"
    assert outcomes == expected
    assert "ProviderTransportError" in output


@pytest.mark.unit
def test_wrong_answer_type_names_the_expected_type(pytester: pytest.Pytester) -> None:
    """The typed-answers failure names the question and the answer type it needs."""
    body = dedent(
        """\
        class TestWrongType(GoodProvider):
            @pytest.fixture
            def provider_port(self):
                return FakeSystemOnePort(answers=INVALID_ANSWERS["noul_for_choice"])
        """
    )
    outcomes, output = _run_output(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected.update(dict.fromkeys(("test_typed_answers_pass_policy",), "FAILED"))
    assert outcomes == expected
    assert "conformance_choice needs ChoiceAnswer, got NoulAnswer" in output


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(_BROKEN))
def test_broken_fake_fails_only_its_rule(pytester: pytest.Pytester, case: str) -> None:
    """Each broken fake fails only its own rule's tests and passes the rest.

    A factory whose port fails validation breaks every scope, so it fails all
    three lifecycle tests of rule 4 and no test of another rule.
    """
    base, fixture, value, failing = _BROKEN[case]
    method = f"@pytest.fixture\ndef {fixture}(self):\n    return {value}\n"
    body = f"class TestBroken({base}):\n{indent(method, '    ')}"
    outcomes = _run(pytester, body)
    expected = dict.fromkeys(RULE_TESTS, "PASSED")
    expected.update(dict.fromkeys(failing, "FAILED"))
    assert outcomes == expected


_ASYNC_GOOD = """\
from contextlib import nullcontext

import pytest

from judgevet.providers import ProviderTransportError
from judgevet.testing import AsyncFakeSystemOnePort, FakeSystemOnePort
from judgevet.testing.conformance import (
    INVALID_ANSWERS,
    VALID_ANSWERS,
    BaseAsyncProviderConformance,
)


class GoodAsyncProvider(BaseAsyncProviderConformance):
    @pytest.fixture
    def provider_factory(self):
        return lambda: nullcontext(AsyncFakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self):
        return AsyncFakeSystemOnePort(error=ProviderTransportError("synthetic"))


class KeywordModelAsyncPort:
    async def system_one(self, state, questions, *, model):
        return await AsyncFakeSystemOnePort(answers=VALID_ANSWERS).system_one(
            state, questions, model
        )


class ReturningAsyncPort:
    async def system_one(self, state, questions, model):
        return await AsyncFakeSystemOnePort(answers=VALID_ANSWERS).system_one(
            state, questions, model
        )


class AsyncContext:
    def __init__(self):
        self.port = AsyncFakeSystemOnePort(answers=VALID_ANSWERS)

    async def __aenter__(self):
        return self.port

    async def __aexit__(self, *exc_info):
        return None


class SwallowingAsyncContext(AsyncContext):
    async def __aexit__(self, *exc_info):
        return True


SHARED_ASYNC = AsyncContext()
"""

_ASYNC_BROKEN = {
    "keyword_only_model": (
        "provider_factory",
        "lambda: nullcontext(KeywordModelAsyncPort())",
        ("test_port_shape",),
    ),
    "wrong_answer_type": (
        "provider_factory",
        'lambda: nullcontext(AsyncFakeSystemOnePort(answers=INVALID_ANSWERS["noul_for_choice"]))',
        ("test_typed_answers_pass_policy",),
    ),
    "sync_port_is_not_awaitable": (
        "provider_factory",
        "lambda: nullcontext(FakeSystemOnePort(answers=VALID_ANSWERS))",
        ("test_typed_answers_pass_policy", "test_scope_entry_yields_usable_port"),
    ),
    "bare_runtime_error": (
        "failing_port",
        'AsyncFakeSystemOnePort(error=RuntimeError("boom"))',
        ("test_failure_raises_provider_error",),
    ),
    "failing_port_returns": (
        "failing_port",
        "ReturningAsyncPort()",
        ("test_failure_raises_provider_error",),
    ),
    "shared_async_context_exits_twice": (
        "provider_factory",
        "lambda: SHARED_ASYNC",
        ("test_scope_exit_runs_once",),
    ),
    "async_context_swallows_body_error": (
        "provider_factory",
        "SwallowingAsyncContext",
        ("test_scope_propagates_body_exception",),
    ),
}


def _run_async(pytester: pytest.Pytester, body: str) -> tuple[dict[str, str], str]:
    """Run one async provider module in a pytest subprocess."""
    pytester.makepyfile(test_async_provider=_ASYNC_GOOD + "\n\n" + body)
    result = pytester.runpytest_subprocess("-v", "-p", "no:cacheprovider")
    output = result.stdout.str()
    outcomes = dict(_OUTCOME.findall(output))
    assert set(outcomes) == set(ASYNC_RULE_TESTS), output
    return outcomes, output


@pytest.mark.unit
def test_good_async_provider_passes_every_rule(pytester: pytest.Pytester) -> None:
    """A correct async provider passes all six async rule tests."""
    body = "class TestGood(GoodAsyncProvider):\n    pass\n"
    outcomes, _ = _run_async(pytester, body)
    assert outcomes == dict.fromkeys(ASYNC_RULE_TESTS, "PASSED")


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(_ASYNC_BROKEN))
def test_broken_async_fake_fails_only_its_rule(
    pytester: pytest.Pytester, case: str
) -> None:
    """Each broken async fake fails only its own rule tests and passes the rest.

    A sync port has no awaitable result, so it fails both rules that await a
    judgment: the typed-answer rule and the scope-entry rule.
    """
    fixture, value, failing = _ASYNC_BROKEN[case]
    method = f"@pytest.fixture\ndef {fixture}(self):\n    return {value}\n"
    body = f"class TestBroken(GoodAsyncProvider):\n{indent(method, '    ')}"
    outcomes, _ = _run_async(pytester, body)
    expected = dict.fromkeys(ASYNC_RULE_TESTS, "PASSED")
    expected.update(dict.fromkeys(failing, "FAILED"))
    assert outcomes == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("sync_port_is_not_awaitable", "not an awaitable"),
        ("bare_runtime_error", "judgevet.providers.ProviderError subclass"),
        ("shared_async_context_exits_twice", "one shared context for two scopes"),
        ("async_context_swallows_body_error", "false value from __aexit__"),
    ],
)
def test_async_failure_names_the_contract(
    pytester: pytest.Pytester, case: str, message: str
) -> None:
    """The async rule failures name the contract the port broke."""
    fixture, value, failing = _ASYNC_BROKEN[case]
    method = f"@pytest.fixture\ndef {fixture}(self):\n    return {value}\n"
    body = f"class TestBroken(GoodAsyncProvider):\n{indent(method, '    ')}"
    outcomes, output = _run_async(pytester, body)
    assert all(outcomes[test] == "FAILED" for test in failing)
    assert message in output


@pytest.mark.unit
def test_async_body_rule_fails_when_the_scope_swallows_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The async body rule fails when the scope itself swallows the exception.

    A provider context cannot model this, so the rule's scope is replaced with
    one that exits the real scope with the error and then drops it.
    """
    real_scope = _conformance_async_scope.async_provider_scope

    @asynccontextmanager
    async def swallowing_scope(
        *, factory: AsyncProviderFactory
    ) -> AsyncIterator[AsyncSystemOnePort]:
        """Run the real scope, then drop the body exception."""
        try:
            async with real_scope(factory=factory) as port:
                yield port
        except BodyError:
            return

    monkeypatch.setattr(
        _conformance_async_scope, "async_provider_scope", swallowing_scope
    )
    kit = BaseAsyncProviderConformance()
    with pytest.raises(pytest.fail.Exception, match="did not propagate"):
        kit.test_scope_propagates_body_exception(
            lambda: nullcontext(AsyncFakeSystemOnePort(answers=VALID_ANSWERS))
        )
