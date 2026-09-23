"""Execute exact documentation programs with synthetic HTTP and no inherited keys.

Examples:
    The parent copies this helper beside the extracted programs in a fresh venv.

See Also:
    - [judgevet][]: Installed package exercised by these examples.
"""

import asyncio
import contextlib
import io
import json
import os
import runpy
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

from judgevet import JevError
from scripts.smoke_release_child import (
    assert_all_names_resolve,
    assert_in_site_packages,
)

SYNC_CLIENT = httpx.Client
ASYNC_CLIENT = httpx.AsyncClient
EXAMPLE_ERRORS = (
    ArithmeticError,
    AssertionError,
    AttributeError,
    ImportError,
    LookupError,
    OSError,
    RuntimeError,
    SyntaxError,
    TypeError,
    ValueError,
    SystemExit,
    httpx.HTTPError,
    JevError,
)


def synthetic_answer(request: httpx.Request) -> httpx.Response:
    """Return a typed synthetic answer for each supplied question.

    Args:
        request: Request produced by the real installed adapter.

    Returns:
        Successful wire body, with matching question names and criteria.

    Raises:
        ValueError: If a question type is unsupported.
    """
    answers = {}
    for name, question in json.loads(request.content)["questions"].items():
        kind = question["type"]
        if kind == "noul":
            answers[name] = {"type": kind, "noul": 0.85}
        elif kind == "choice":
            labels = list(question["criteria"])
            answers[name] = {
                "type": kind,
                "choice": labels[0],
                "confidence": 0.8,
                "probabilities": {
                    label: float(i == 0) for i, label in enumerate(labels)
                },
            }
        elif kind == "score":
            levels = question["criteria"]
            answers[name] = {
                "type": kind,
                "score": 0.0,
                "confidence": 0.8,
                "legend": dict(enumerate(levels)),
                "probabilities": {i: float(i == 0) for i in range(len(levels))},
            }
        else:
            raise ValueError("unsupported synthetic question type")
    return httpx.Response(
        200,
        json={
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 10, "output_tokens": 1},
            "answers": answers,
        },
    )


def run_example(path: Path, label: str) -> str | None:
    """Run one unchanged program, reject failures and require closed clients.

    Args:
        path: Exact extracted Python file.
        label: Source page and block location.

    Returns:
        A bounded diagnostic, or None when execution and cleanup pass.
    """
    clients: list[httpx.Client | httpx.AsyncClient] = []

    def sync(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(synthetic_answer)
        client = SYNC_CLIENT(**kwargs)
        clients.append(client)
        return client

    def asynchronous(**kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(synthetic_answer)
        client = ASYNC_CLIENT(**kwargs)
        clients.append(client)
        return client

    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, offline_env(), clear=True))
            stack.enter_context(patch("httpx.Client", sync))
            stack.enter_context(patch("httpx.AsyncClient", asynchronous))
            for target in ("create_connection", "getaddrinfo", "socket.connect"):
                stack.enter_context(
                    patch(
                        f"socket.{target}", side_effect=RuntimeError("network disabled")
                    )
                )
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            runpy.run_path(str(path), run_name="__main__")
        if any(not client.is_closed for client in clients):
            return f"{label}: unclosed client"
    except EXAMPLE_ERRORS as error:
        return f"{label}: {type(error).__name__} during exact example execution"
    finally:
        for client in clients:
            if isinstance(client, ASYNC_CLIENT):
                asyncio.run(client.aclose())
            else:
                client.close()
    return None


def offline_env() -> dict[str, str]:
    """Build a key-free inherited environment with only synthetic credentials.

    Returns:
        Fixed dummy credentials; no caller environment values.
    """
    return {
        "JEV_API__KEY": "synthetic-doc-key",
        "TYPESAFE_API_KEY": "synthetic-doc-key",
    }


def main() -> int:
    """Execute the parent's manifest inside the isolated installation.

    Returns:
        One if any exact example fails, otherwise zero.
    """
    assert_in_site_packages()
    assert_all_names_resolve()
    jobs = json.loads(Path("python_examples.json").read_text())
    if not jobs:
        print("Python documentation: empty executable inventory")
        return 1
    findings = [run_example(Path(job["file"]), job["label"]) for job in jobs]
    for finding in findings:
        if finding:
            print(finding)
    print(f"Python documentation: executed {len(jobs)} exact programs offline")
    return int(any(findings))


if __name__ == "__main__":
    raise SystemExit(main())
