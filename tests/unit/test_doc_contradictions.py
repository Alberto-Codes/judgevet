"""Pin documentation sentences that once contradicted the shipped code.

Issue #285 corrected each sentence below. Each test reads one page and fails
unless the exact corrected sentence, markup included, is present. A later edit
that reverts or drifts a sentence fails this gate.

Examples:
    ```python
    page = "The default is three attempts."
    assert "three attempts" in page
    ```

See Also:
    - [judgevet.adapters.inbound.mcp_policy][]: The MCP policy tool.
    - [judgevet.adapters.outbound.audit_jsonl][]: The opt-in audit sink.
    - [judgevet.adapters.outbound.retries][]: The default retry policy.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "docs/explanation/architecture.md"
ERRORS = ROOT / "docs/reference/errors.md"
SECURITY = ROOT / "SECURITY.md"
REQUEST_SVG = ROOT / "docs/assets/request-data.svg"

MCP_POLICY_TOOL = (
    "MCP exposes the `evaluate_policy` tool since release 0.14.0; see the\n"
    "[MCP policy adapter](../../src/judgevet/adapters/inbound/mcp_policy.py)."
)
POLICY_ENTRY_POINTS = (
    "For policy use, choose the Python API, the CLI's policy option or that MCP tool."
)
RETRIES_ON_BY_DEFAULT = "Retries are on by default and remain in the outbound adapter."
AUDIT_SINK_OPT_IN = (
    "An opt-in `JsonlAuditSink`, opened from `JEV_API__AUDIT_PATH`, appends the "
    "records that\n[the audit sink module]"
    "(../../src/judgevet/adapters/outbound/audit_jsonl.py) documents."
)
NO_REDACTION = (
    "No pre-send content redaction or retention control is part of this path."
)
RETRY_DEFAULT = (
    "The default is three attempts; see\n"
    "[the retry module](../../src/judgevet/adapters/outbound/retries.py)."
)
REVIEW_SCOPE = (
    "The credential, transport and diagnostic review below was performed against\n"
    "release 0.6.0. Later releases were not re-reviewed."
)
NO_STATE_STORE = "The request path has no persistent credential or state store."
SINK_MODE = (
    "The sink creates the file with mode `0o600` if absent and appends\n"
    "one JSON line per judgment. Each line carries every `JudgmentRecord` field;\n"
    "success lines include the answers and the usage."
)
SHIPPED_FEATURES = (
    "Certificate pinning, a judgevet mTLS configuration,\n"
    "encrypted storage and enterprise audit controls are not shipped features."
)
SVG_POLICY = (
    "Python, the CLI or the MCP evaluate_policy tool can evaluate a policy locally."
)


def assert_page_states(page: Path, sentence: str) -> None:
    """Fail unless the page carries the exact corrected sentence.

    Args:
        page: The source file to read.
        sentence: The corrected sentence, markup and line breaks included.

    Raises:
        AssertionError: The page lacks the sentence.
    """
    text = page.read_text(encoding="utf-8")
    assert sentence in text, f"{page.name} is missing the sentence: {sentence}"


@pytest.mark.unit
def test_architecture_names_the_mcp_policy_tool():
    assert_page_states(ARCHITECTURE, MCP_POLICY_TOOL)


@pytest.mark.unit
def test_architecture_lists_mcp_among_policy_entry_points():
    assert_page_states(ARCHITECTURE, POLICY_ENTRY_POINTS)


@pytest.mark.unit
def test_architecture_states_retries_are_on_by_default():
    assert_page_states(ARCHITECTURE, RETRIES_ON_BY_DEFAULT)


@pytest.mark.unit
def test_architecture_names_the_opt_in_audit_sink():
    assert_page_states(ARCHITECTURE, AUDIT_SINK_OPT_IN)


@pytest.mark.unit
def test_architecture_keeps_the_no_redaction_limit():
    assert_page_states(ARCHITECTURE, NO_REDACTION)


@pytest.mark.unit
def test_errors_page_states_three_default_attempts():
    assert_page_states(ERRORS, RETRY_DEFAULT)


@pytest.mark.unit
def test_security_dates_the_review_to_release_0_6_0():
    assert_page_states(SECURITY, REVIEW_SCOPE)


@pytest.mark.unit
def test_security_drops_the_no_answer_store_claim():
    assert_page_states(SECURITY, NO_STATE_STORE)


@pytest.mark.unit
def test_security_states_the_sink_file_mode():
    assert_page_states(SECURITY, SINK_MODE)


@pytest.mark.unit
def test_security_scope_carries_no_version():
    assert_page_states(SECURITY, SHIPPED_FEATURES)


@pytest.mark.unit
def test_request_diagram_names_the_mcp_policy_tool():
    assert_page_states(REQUEST_SVG, SVG_POLICY)
