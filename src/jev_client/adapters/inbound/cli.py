"""Inbound CLI adapter.

Examples:
    ```python
    from jev_client.adapters.inbound.cli import app
    # Run CLI: jev --help
    ```

See Also:
    - [jev_client.adapters.inbound.settings][]: Settings for configuration
    - [jev_client.adapters.outbound.http][]: HTTP adapter
    - [jev_client.domain.response_parser][]: Response parsing
    - [jev_client.domain.questions][]: Question types
    - [jev_client.domain.answers][]: Answer types
    - [jev_client.domain.errors][]: Error types
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import typer

from jev_client.adapters.inbound.settings import Settings
from jev_client.adapters.outbound.http import HTTPSystemOneAdapter
from jev_client.domain.answers import (
    Answer,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from jev_client.domain.errors import (
    JevAuthError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from jev_client.domain.questions import Choice, Noul, Score
from jev_client.domain.response import SystemOneResponse

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
    state: str,
    questions: str,
    model: str = "jev-latest",
    api_key: str | None = None,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> int:
    """Run the CLI with parsed arguments.

    The CLI constructs Settings and uses them for configuration.
    Values from Settings are used as defaults unless explicitly overridden by
    command-line options.

    Args:
        state: State to evaluate (JSON string or text).
        questions: Questions as JSON string.
        model: Model to use. Defaults to Settings.api.default_model.
        api_key: TypeSafe API key. Overrides Settings.api.key if provided.
        json_output: Whether to output as JSON.

    Returns:
        Exit code: 0 for success, 1 for error.

    Raises:
        JevAuthError: If authentication fails.
        JevRequestError: If the request fails with 4xx.
        JevServiceError: If the service fails with 5xx or transport error.
        JevResponseError: If the response body cannot be parsed.
    """
    settings = Settings()
    base_url = settings.api.base_url
    key = settings.api.key.get_secret_value() if settings.api.key else None

    # Explicit --api-key wins over settings value
    final_api_key = api_key if api_key is not None else key

    try:
        adapter = HTTPSystemOneAdapter(
            api_key=final_api_key,
            base_url=base_url,
            default_model=model,
        )

        state_data = json.loads(state) if state.startswith(("{", "[")) else state
        questions_dict = parse_questions(questions)

        response = adapter.system_one(
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
        adapter.close()
        return 0


@app.command()
def main(
    state: str = typer.Argument(..., help="State to evaluate (JSON string or text)"),
    questions: str = typer.Argument(..., help="Questions as JSON string"),
    model: str = typer.Option("jev-latest", help="Model to use"),
    api_key: str | None = typer.Option(None, help="TypeSafe API key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> int:
    """Call the Jev System One API.

    Args:
        state: State to evaluate (JSON string or text).
        questions: Questions as JSON string.
        model: Model to use.
        api_key: TypeSafe API key.
        json_output: Whether to output as JSON.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    return run_cli(state, questions, model, api_key, json_output)


def cli_main() -> int:
    """CLI entry point for backward compatibility.

    This function is kept for backward compatibility with tests.
    It parses arguments using the old argparse-based parse_args function.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    args = parse_args()
    return run_cli(
        args.state,
        args.questions,
        args.model,
        args.api_key,
        args.json,
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
