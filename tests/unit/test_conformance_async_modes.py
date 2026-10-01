"""Acceptance tests for the async conformance kit under pytest-asyncio (#257).

A provider project that runs pytest-asyncio in `asyncio_mode = "auto"` must
still get correct results from `BaseAsyncProviderConformance`. Each test runs
the kit in a pytester subprocess with its own ini file, so the repository's
own pytest configuration and its default strict mode do not leak in.
Source: https://github.com/Alberto-Codes/judgevet/issues/257#issuecomment-5903746299.
Source: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html.
"""

from __future__ import annotations

from textwrap import indent

import pytest

from tests.unit.test_conformance_kit import (
    _ASYNC_BROKEN,
    _ASYNC_GOOD,
    _OUTCOME,
    ASYNC_RULE_TESTS,
)

pytest_plugins = ["pytester"]

_AUTO_HEADER = "asyncio: mode=Mode.AUTO"
_AUTHOR_TEST = "test_author_coroutine_runs_under_auto_mode"
_AUTHOR_BODY = f"""

async def {_AUTHOR_TEST}():
    import asyncio

    await asyncio.sleep(0)
"""


def _run_auto(pytester: pytest.Pytester, body: str) -> dict[str, str]:
    """Run one async provider module under pytest-asyncio auto mode.

    The module also carries an undecorated coroutine test. Only auto mode
    runs that test; strict mode leaves it unhandled and it does not pass.

    Args:
        pytester: The pytester fixture that owns the temporary project.
        body: Provider test classes appended to the shared async module.

    Returns:
        A map from each test name to its outcome.
    """
    pytester.makeini("[pytest]\nasyncio_mode = auto\n")
    source = _ASYNC_GOOD + "\n\n" + body + _AUTHOR_BODY
    pytester.makepyfile(test_async_provider=source)
    result = pytester.runpytest_subprocess("-v", "-p", "no:cacheprovider")
    output = result.stdout.str()
    assert _AUTO_HEADER in output, output
    outcomes = dict(_OUTCOME.findall(output))
    assert set(outcomes) == {*ASYNC_RULE_TESTS, _AUTHOR_TEST}, output
    assert outcomes.pop(_AUTHOR_TEST) == "PASSED", output
    return outcomes


@pytest.mark.unit
def test_good_async_provider_passes_under_auto_mode(
    pytester: pytest.Pytester,
) -> None:
    """The async fake passes all six async rules under auto mode."""
    body = "class TestGood(GoodAsyncProvider):\n    pass\n"
    outcomes = _run_auto(pytester, body)
    assert outcomes == dict.fromkeys(ASYNC_RULE_TESTS, "PASSED")


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(_ASYNC_BROKEN))
def test_broken_async_fake_fails_only_its_rule_under_auto_mode(
    pytester: pytest.Pytester, case: str
) -> None:
    """Each broken async fake fails only its own rule under auto mode."""
    fixture, value, failing = _ASYNC_BROKEN[case]
    method = f"@pytest.fixture\ndef {fixture}(self):\n    return {value}\n"
    body = f"class TestBroken(GoodAsyncProvider):\n{indent(method, '    ')}"
    outcomes = _run_auto(pytester, body)
    expected = dict.fromkeys(ASYNC_RULE_TESTS, "PASSED")
    expected.update(dict.fromkeys(failing, "FAILED"))
    assert outcomes == expected
