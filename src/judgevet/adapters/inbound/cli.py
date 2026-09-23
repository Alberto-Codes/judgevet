"""Inbound CLI adapter.

The command wrapper propagates failure status to the process while helpers
return integer codes and the composition root closes its adapter. Explicit
file and stdin sources are validated before adapter construction. Explicit
policies use a separate composition path and distinguish unmet policy from errors.
Both paths resolve credential sources once before adapter construction.
They render rate limits as handled failures and configure stderr logging.

Examples:
    ```python
    from judgevet.adapters.inbound.cli import app
    # Run CLI: judgevet --help
    ```

See Also:
    - [judgevet.adapters.inbound.settings][]: Settings for configuration
    - [judgevet.adapters.outbound.http][]: HTTP adapter
    - [judgevet.ports][]: Port protocol
    - [judgevet.domain.response][]: Response types
    - [judgevet.domain.questions][]: Question types
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.errors][]: Error types
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Annotated, Any

import typer

from judgevet.adapters.inbound.cli_inputs import InputFailure, resolve_inputs
from judgevet.adapters.inbound.cli_policy_run import CliCallbacks, run_policy
from judgevet.adapters.inbound.logs import configure
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.answers import (
    Answer,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from judgevet.domain.errors import (
    JevAuthError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import SystemOnePort

MAX_POSITIONAL_INPUTS = 2

app = typer.Typer(help="Call the Jev System One API")

__all__ = ["app", "cli_main"]


def parse_questions(questions_json: str) -> dict[str, Any]:
    """Parse questions from JSON string.

    Args:
        questions_json: JSON string defining questions.

    Returns:
        Dictionary mapping question names to question objects.

    Raises:
        ValueError: If an unknown question type is encountered.
    """
    data = json.loads(questions_json)
    result = {}
    for name, question_data in data.items():
        qtype = question_data.get("type")
        if qtype == "noul":
            result[name] = Noul(
                instructions=question_data.get("instructions"),
                criteria=question_data.get("criteria"),
            )
        elif qtype == "choice":
            result[name] = Choice(
                criteria=question_data.get("criteria", {}),
                instructions=question_data.get("instructions"),
            )
        elif qtype == "score":
            result[name] = Score(
                criteria=question_data.get("criteria", []),
                instructions=question_data.get("instructions"),
            )
        else:
            raise ValueError(f"Unknown question type: {qtype}")
    return result


def format_answer(name: str, answer: Answer) -> dict[str, Any]:
    """Format an answer as a dictionary.

    Args:
        name: Question name.
        answer: The answer object.

    Returns:
        Dictionary representation of the answer.

    Raises:
        TypeError: If the answer type is unknown.
    """
    if isinstance(answer, NoulAnswer):
        return {"name": name, "type": "noul", "noul": answer.noul}
    elif isinstance(answer, ChoiceAnswer):
        return {
            "name": name,
            "type": "choice",
            "choice": answer.choice,
            "confidence": answer.confidence,
            "probabilities": answer.probabilities,
        }
    elif isinstance(answer, ScoreAnswer):
        return {
            "name": name,
            "type": "score",
            "score": answer.score,
            "confidence": answer.confidence,
            "legend": answer.legend,
            "probabilities": answer.probabilities,
        }
    else:
        raise TypeError(f"Unknown answer type: {type(answer)}")


def build_response_data(response: SystemOneResponse) -> dict[str, Any]:
    """Build response data dictionary from a typed SystemOneResponse.

    Args:
        response: Typed SystemOneResponse from the adapter.

    Returns:
        Response data dictionary for output.
    """
    answers = {name: format_answer(name, ans) for name, ans in response.answers.items()}
    return {
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "answers": answers,
    }


def output_response(response_data: dict[str, Any], as_json: bool) -> None:
    """Output response data.

    Args:
        response_data: Response data dictionary.
        as_json: Whether to output as JSON.
    """
    if as_json:
        print(json.dumps(response_data, indent=2))
    else:
        print(f"Model: {response_data['model']}")
        print(f"Usage: {response_data['usage']}")
        print("Answers:")
        for formatted in response_data["answers"].values():
            print(f"  {formatted['name']}: {formatted}")


def run_cli(
    port: SystemOnePort,
    state: str,
    questions: str,
    model: str = "jev-latest",
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> int:
    """Run the CLI with a port and render handled errors, including rate limits.

    Args:
        port: The port used for API calls.
        state: State to evaluate (JSON string or text).
        questions: Questions as JSON string.
        model: Model to use. Defaults to "jev-latest".
        json_output: Whether to output as JSON.

    Returns:
        Exit code: 0 for success, 1 for judgment errors.
    """
    try:
        state_data = json.loads(state) if state.startswith(("{", "[")) else state
        questions_dict = parse_questions(questions)

        response = port.system_one(
            state=state_data, questions=questions_dict, model=model
        )

        response_data = build_response_data(response)

        output_response(response_data, json_output)
    except (
        ValueError,
        json.JSONDecodeError,
        TypeError,
        KeyError,
        JevAuthError,
        JevRateLimitError,
        JevRequestError,
        JevResponseError,
        JevServiceError,
    ) as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    else:
        return 0


def _command_inputs(
    state: str | None,
    questions: str | None,
    state_files: list[str] | None,
    question_files: list[str] | None,
    policy_files: list[str] | None,
    as_json: bool,
) -> tuple[str, str]:
    """Resolve explicit input sources before either judgment composition path.

    Args:
        state: Legacy state positional argument.
        questions: Legacy questions positional argument.
        state_files: Explicit state source options.
        question_files: Explicit questions source options.
        policy_files: Explicit policy source options.
        as_json: Select machine diagnostics.

    Returns:
        Resolved state and questions strings.

    Raises:
        typer.Exit: If explicit sources conflict or contain invalid input.
        typer.BadParameter: If legacy positional arguments are missing.
    """
    if policy_files and len(policy_files) > 1:
        message = "--policy: specify one policy file"
        print(
            json.dumps({"error": message}) if as_json else f"Error: {message}",
            file=sys.stderr,
        )
        raise typer.Exit(2)
    try:
        if state_files or question_files or policy_files:
            state, questions = resolve_inputs(
                state,
                questions,
                state_files or [],
                question_files or [],
                parse_questions,
            )
    except InputFailure as exc:
        print(
            json.dumps({"error": str(exc)}) if as_json else f"Error: {exc}",
            file=sys.stderr,
        )
        raise typer.Exit(exc.code) from None
    if state is None or questions is None:
        raise typer.BadParameter("State and questions are required")
    return state, questions


@app.command(help="Call the Jev System One API.")
def _cli_command(
    arguments: Annotated[
        list[str] | None,
        typer.Argument(
            help=("state: State to evaluate. questions: Questions as JSON string."),
            metavar="[STATE] [QUESTIONS]",
        ),
    ] = None,
    model: str = typer.Option("jev-latest", help="Model to use"),
    api_key: str | None = typer.Option(None, help="TypeSafe API key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    *,
    state_files: Annotated[
        list[str] | None,
        typer.Option(
            "--state-file", help="Read UTF-8 state from a file; - reads stdin"
        ),
    ] = None,
    question_files: Annotated[
        list[str] | None,
        typer.Option("--questions-file", help="Read questions from a UTF-8 JSON file"),
    ] = None,
    policy_files: Annotated[
        list[str] | None,
        typer.Option("--policy", help="Apply an explicit acceptance policy from JSON"),
    ] = None,
) -> int:
    """Validate command inputs and dispatch to the selected composition root.

    Args:
        arguments: Optional positional state followed by questions JSON.
        model: Model to use.
        api_key: TypeSafe API key.
        json_output: Output as JSON.
        state_files: Explicit state source, specified at most once.
        question_files: Explicit questions source, specified at most once.
        policy_files: Explicit policy source, specified at most once.

    Returns:
        0 on success. Failures raise typer.Exit.

    Raises:
        typer.Exit: If input validation or the judgment fails.
        typer.BadParameter: If required legacy positional arguments are absent.
    """
    positions = arguments or []
    if len(positions) > MAX_POSITIONAL_INPUTS:
        raise typer.BadParameter("Expected at most state and questions")
    state = positions[0] if positions else None
    questions = positions[1] if len(positions) == MAX_POSITIONAL_INPUTS else None
    state, questions = _command_inputs(
        state, questions, state_files, question_files, policy_files, json_output
    )
    code = _dispatch(state, questions, model, api_key, json_output, policy_files)
    if code != 0:
        raise typer.Exit(code=code)
    return code


def _dispatch(
    state: str,
    questions: str,
    model: str,
    api_key: str | None,
    json_output: bool,
    policy_files: list[str] | None,
) -> int:
    """Select the composition path after command input validation.

    Args:
        state: Validated state text.
        questions: Validated question text.
        model: Requested model.
        api_key: Optional explicit literal key.
        json_output: Select JSON rendering.
        policy_files: Optional validated policy file selection.

    Returns:
        Exit status from the selected composition root.
    """
    if policy_files:
        return run_policy(
            state,
            questions,
            model,
            api_key,
            json_output,
            policy_files[0],
            CliCallbacks(parse_questions, build_response_data, output_response),
        )
    else:
        return main(
            state=state,
            questions=questions,
            model=model,
            api_key=api_key,
            json_output=json_output,
        )


def main(
    state: str = typer.Argument(..., help="State to evaluate (JSON string or text)"),
    questions: str = typer.Argument(..., help="Questions as JSON string"),
    model: str = typer.Option("jev-latest", help="Model to use"),
    api_key: str | None = typer.Option(None, help="TypeSafe API key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> int:
    """Call the Jev System One API.

    Reads Settings and configures stderr logging. An explicit --api-key overrides
    the selected credential source. Resolves it once as a wrapped key.
    Constructs HTTPSystemOneAdapter once with the settings
    timeout, network options and retry limits, then calls run_cli with it as the port.
    Closes the adapter in finally.
    The command wrapper supplies separate help and propagates failure status.

    Args:
        state: State to evaluate (JSON string or text).
        questions: Questions as JSON string.
        model: Model to use.
        api_key: TypeSafe API key.
        json_output: Whether to output as JSON.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    settings = Settings()
    configure(settings.log)
    timeout_seconds = settings.api.timeout_seconds
    base_url = settings.api.base_url
    try:
        key = settings.api.resolve_key(api_key)
    except ValueError:
        message = "API key source failed"
        print(
            json.dumps({"error": message}) if json_output else f"Error: {message}",
            file=sys.stderr,
        )
        return 1

    adapter = HTTPSystemOneAdapter(
        api_key=key.get_secret_value() if key is not None else None,
        base_url=base_url,
        default_model=model,
        timeout_seconds=timeout_seconds,
        retry=settings.api.retry_policy,
        network=settings.api.network_config,
    )

    try:
        return run_cli(
            port=adapter,
            state=state,
            questions=questions,
            model=model,
            json_output=json_output,
        )
    finally:
        adapter.close()


def cli_main() -> int:
    """CLI entry point for backward compatibility.

    Parses sys.argv with parse_args and delegates to main.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    args = parse_args()
    return main(
        state=args.state,
        questions=args.questions,
        model=args.model,
        api_key=args.api_key,
        json_output=args.json,
    )


def parse_args() -> Any:
    """Parse command line arguments.

    This function is kept for backward compatibility with tests.
    It creates a temporary argparse parser to parse arguments.

    Returns:
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Call the Jev System One API")
    parser.add_argument("state", help="State to evaluate (JSON string or text)")
    parser.add_argument("questions", help="Questions as JSON string")
    parser.add_argument("--model", default="jev-latest", help="Model to use")
    parser.add_argument("--api-key", help="TypeSafe API key")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(app())
