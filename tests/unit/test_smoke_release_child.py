"""Tests for scripts/smoke_release_child.py.

These tests exercise the live check execution logic for issue #107 repair:
per-block placeholder validation, correct async dispatch, and layout failures
while execution continues for valid blocks.
"""

from __future__ import annotations

import pytest

import scripts.smoke_release_child
from scripts.smoke_release_child import run_live_checks


def _fake_judgevet(docstring: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a fake module with the given docstring and patch the getter."""

    class _Module:
        __doc__ = docstring

    monkeypatch.setattr(
        scripts.smoke_release_child, "__get_judgevet_module", lambda: _Module
    )


class TestRunLiveChecks:
    """Tests for run_live_checks function."""

    def test_sync_canary_reports_count_and_type_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sync example that raises TypeError reports TypeError message."""
        doc = """Module doc.

Examples:
    ```python
    # your-api-key
    raise TypeError("Object of type Noul is not JSON serializable")
    ```
"""
        _fake_judgevet(doc, monkeypatch)
        failures = run_live_checks("canary-test-key")
        assert any("Expected 2 python blocks, found 1" in f for f in failures)
        assert any(
            "sync example 0 failed" in f
            and "TypeError: Object of type Noul is not JSON serializable" in f
            for f in failures
        )

    @pytest.mark.parametrize(
        ("doc", "await_count"),
        [
            (
                """Module doc.

Examples:
    ```python
    # your-api-key
    print("one-executed")
    ```

    ```python
    # your-api-key
    print("two-executed")
    ```
""",
                0,
            ),
            (
                """Module doc.

Examples:
    ```python
    # your-api-key
    import asyncio
    await asyncio.sleep(0)
    print("one-executed")
    ```

    ```python
    # your-api-key
    import asyncio
    await asyncio.sleep(0)
    print("two-executed")
    ```
""",
                2,
            ),
        ],
        ids=["two-sync", "two-async"],
    )
    def test_two_blocks_retains_layout_failure_and_both_execute(
        self,
        doc: str,
        await_count: int,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Two sync or two async blocks retain layout failure but both execute."""
        _fake_judgevet(doc, monkeypatch)
        failures = run_live_checks("canary-test-key")
        assert any(
            f"Expected exactly 1 block with 'await', found {await_count}" in f
            for f in failures
        )
        assert not any("python blocks" in f for f in failures)
        out = capsys.readouterr().out
        assert "one-executed" in out and "two-executed" in out

    def test_reversed_order_executes_both_and_passes(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Async block first (importing asyncio), then sync: both execute, no failures."""
        doc = """Module doc.

Examples:
    ```python
    # your-api-key
    import asyncio
    await asyncio.sleep(0)
    print("async-executed")
    ```

    ```python
    # your-api-key
    print("sync-executed")
    print("your-api-key")
    ```
"""
        _fake_judgevet(doc, monkeypatch)
        assert run_live_checks("canary-test-key") == []
        out = capsys.readouterr().out.splitlines()
        assert out == ["async-executed", "sync-executed", "canary-test-key"]

    def test_no_blocks_stays_red(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Zero blocks is a layout failure, no execution attempted."""
        doc = """No examples."""
        _fake_judgevet(doc, monkeypatch)
        failures = run_live_checks("canary-test-key")
        assert any("Expected 2 python blocks, found 0" in f for f in failures)
        assert capsys.readouterr().out == ""

    def test_invalid_block_first_skip_and_run_valid(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Invalid block (no placeholder) in position 0 is skipped, valid block runs."""
        doc = """Module doc.

Examples:
    ```python
    print("invalid-executed")
    ```

    ```python
    # your-api-key
    import asyncio
    await asyncio.sleep(0)
    print("valid-executed")
    ```
"""
        _fake_judgevet(doc, monkeypatch)
        failures = run_live_checks("canary-test-key")
        assert failures == ["Block 0 missing key placeholder"]
        out = capsys.readouterr().out
        assert "invalid-executed" not in out
        assert "valid-executed" in out

    def test_invalid_block_second_skip_and_run_valid(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Valid block in position 0, invalid in position 1: invalid skipped, valid runs."""
        doc = """Module doc.

Examples:
    ```python
    # your-api-key
    import asyncio
    await asyncio.sleep(0)
    print("valid-executed")
    ```

    ```python
    print("invalid-executed")
    ```
"""
        _fake_judgevet(doc, monkeypatch)
        failures = run_live_checks("canary-test-key")
        assert failures == ["Block 1 missing key placeholder"]
        out = capsys.readouterr().out
        assert "valid-executed" in out
        assert "invalid-executed" not in out
