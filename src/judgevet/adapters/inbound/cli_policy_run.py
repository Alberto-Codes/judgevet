"""Compose policy judgments with explicit adapter ownership and safe diagnostics.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_policy_run import run_policy

    assert callable(run_policy)
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Legacy parsing and output callbacks.
    - [judgevet.adapters.inbound.cli_policy][]: Local policy validation.
    - [judgevet.adapters.inbound.cli_policy_eval][]: Typed answer evaluation.
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import Rule, parse_policy
from judgevet.adapters.inbound.cli_policy_eval import evaluate_policy
from judgevet.adapters.inbound.logs import configure
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import (
    JevAuthError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse


@dataclass(frozen=True)
class CliCallbacks:
    """Reuse the legacy CLI parsing and rendering boundaries.

    Attributes:
        parse (Callable): Parse question JSON into typed questions.
        build (Callable): Format a typed answer envelope.
        output (Callable): Render the envelope in the selected mode.

    Examples:
        ```python
        from judgevet.adapters.inbound.cli import (
            parse_questions,
            build_response_data,
            output_response,
        )

        callbacks = CliCallbacks(parse_questions, build_response_data, output_response)
        assert callable(callbacks.parse)
        ```
    """

    parse: Callable[[str], dict[str, Question]]
    build: Callable[[SystemOneResponse], dict[str, Any]]
    output: Callable[[dict[str, Any], bool], None]


def _load_policy(path: str, questions: dict[str, Question]) -> tuple[Rule, ...]:
    """Read a policy file without exposing its path or contents in diagnostics.

    Args:
        path: Explicit policy path.
        questions: Validated typed questions referenced by the policy.

    Returns:
        Ordered validated rules.

    Raises:
        InputFailure: If reading, decoding or schema validation fails.
    """
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        raise InputFailure("--policy: cannot read UTF-8 policy file") from None
    return parse_policy(text, questions)


def _render_policy(
    response: SystemOneResponse,
    rules: tuple[Rule, ...],
    as_json: bool,
    build: Callable[[SystemOneResponse], dict[str, Any]],
    output: Callable[[dict[str, Any], bool], None],
) -> int:
    """Evaluate before emitting answers and render the explicit policy report.

    Args:
        response: Typed answer envelope.
        rules: Ordered validated rules.
        as_json: Select machine output.
        build: Existing answer-envelope formatter.
        output: Existing answer renderer.

    Returns:
        Zero if every rule passes, otherwise policy-unmet status three.

    Raises:
        InputFailure: If a required answer is missing or invalid.
    """
    passed, reports = evaluate_policy(rules, response.answers)
    data = build(response)
    data["policy"] = {"result": "pass" if passed else "fail", "rules": reports}
    output(data, as_json)
    if not as_json:
        print(f"Policy: {'PASS' if passed else 'FAIL'}", file=sys.stderr)
        for report in reports:
            verdict = "pass" if report["pass"] else "fail"
            print(
                f"[{verdict}] {report['question']}: {report['detail']}", file=sys.stderr
            )
    return 0 if passed else 3


def _build_adapter(
    settings: Settings, api_key: str | None, model: str
) -> HTTPSystemOneAdapter:
    """Resolve the policy credential once and construct its configured adapter.

    Args:
        settings: Validated connection, retry and network settings.
        api_key: Optional explicit key override.
        model: Requested model.

    Returns:
        An owned HTTP adapter for one policy invocation.

    Raises:
        ValueError: If credential resolution or connection configuration fails.
    """
    key = settings.api.resolve_key(api_key)
    return HTTPSystemOneAdapter(
        api_key=key.get_secret_value() if key is not None else None,
        base_url=settings.api.base_url,
        default_model=model,
        timeout_seconds=settings.api.timeout_seconds,
        retry=settings.api.retry_policy,
        network=settings.api.network_config,
    )


def run_policy(
    state: str,
    questions: str,
    model: str,
    api_key: str | None,
    as_json: bool,
    policy_file: str,
    callbacks: CliCallbacks,
) -> int:
    """Validate policy, build its configured adapter and close after judgment.

    Args:
        state: Existing state string interpretation.
        questions: Existing question JSON.
        model: Explicit model argument.
        api_key: Explicit key override, if supplied.
        as_json: Select machine output.
        policy_file: Explicit policy file path.
        callbacks: Existing parsing and rendering boundaries.

    Returns:
        Zero for met policy, three for unmet policy, or one for an input/service error.
    """
    try:
        typed_questions = callbacks.parse(questions)
        rules = _load_policy(policy_file, typed_questions)
        state_data = json.loads(state) if state.startswith(("{", "[")) else state
        settings = Settings()
        configure(settings.log)
        adapter = _build_adapter(settings, api_key, model)
        try:
            response = adapter.system_one(
                state=state_data, questions=typed_questions, model=model
            )
            return _render_policy(
                response, rules, as_json, callbacks.build, callbacks.output
            )
        finally:
            adapter.close()
    except InputFailure as error:
        message = str(error)
    except (
        JevAuthError,
        JevRateLimitError,
        JevRequestError,
        JevResponseError,
        JevServiceError,
    ) as error:
        message = str(error)
    except (ValueError, TypeError, KeyError, AttributeError):
        message = "Invalid state, questions or configuration for policy judgment"
    print(
        json.dumps({"error": message}) if as_json else f"Error: {message}",
        file=sys.stderr,
    )
    return 1
