"""Inbound CLI adapter."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from jev_client.adapters.outbound.http import HTTPSystemOneAdapter
from jev_client.domain.answers import (
    Answer,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from jev_client.domain.questions import Choice, Noul, Score


def parse_questions(questions_json: str) -> dict[str, Any]:
    """Parse questions from JSON string.

    Args:
        questions_json: JSON string defining questions.

    Returns:
        Dictionary mapping question names to question objects.
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Call the Jev System One API")
    parser.add_argument("state", help="State to evaluate (JSON string or text)")
    parser.add_argument("questions", help="Questions as JSON string")
    parser.add_argument("--model", default="jev-latest", help="Model to use")
    parser.add_argument("--api-key", help="TypeSafe API key")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    return parser.parse_args()


def build_response_data(
    raw_response: dict[str, Any], answers: dict[str, Answer]
) -> dict[str, Any]:
    """Build response data dictionary.

    Args:
        raw_response: Raw API response.
        answers: Parsed answer objects.

    Returns:
        Response data dictionary.
    """
    return {
        "model": raw_response["model"],
        "usage": {
            "input_tokens": raw_response["usage"].get("input_tokens"),
            "output_tokens": raw_response["usage"].get("output_tokens"),
        },
        "answers": {name: format_answer(name, ans) for name, ans in answers.items()},
    }


def main() -> int:
    """CLI entry point."""
    args = parse_args()

    try:
        adapter = HTTPSystemOneAdapter(api_key=args.api_key)

        state = (
            json.loads(args.state)
            if args.state.startswith("{") or args.state.startswith("[")
            else args.state
        )
        questions = parse_questions(args.questions)

        raw_response = adapter.system_one(
            state=state, questions=questions, model=args.model
        )

        answers = parse_raw_answers(raw_response)
        response_data = build_response_data(raw_response, answers)

        output_response(response_data, args.json)

        adapter.close()
        return 0

    except Exception as e:  # noqa: BLE001
        if args.json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def parse_raw_answers(raw_response: dict[str, Any]) -> dict[str, Answer]:
    """Parse raw API answers into domain objects.

    Args:
        raw_response: Raw API response.

    Returns:
        Dictionary of answer objects.
    """
    answers: dict[str, Answer] = {}
    for name, raw_answer in raw_response.get("answers", {}).items():
        atype = raw_answer.get("type")
        if atype == "noul":
            answers[name] = NoulAnswer(noul=raw_answer["noul"])
        elif atype == "choice":
            answers[name] = ChoiceAnswer(
                choice=raw_answer["choice"],
                confidence=raw_answer["confidence"],
                probabilities=raw_answer["probabilities"],
            )
        elif atype == "score":
            legend = {int(k): v for k, v in raw_answer["legend"].items()}
            probabilities = {int(k): v for k, v in raw_answer["probabilities"].items()}
            answers[name] = ScoreAnswer(
                score=raw_answer["score"],
                confidence=raw_answer["confidence"],
                legend=legend,
                probabilities=probabilities,
            )
        else:
            print(f"Warning: Unknown answer type {atype}", file=sys.stderr)
    return answers


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


if __name__ == "__main__":
    sys.exit(main())
