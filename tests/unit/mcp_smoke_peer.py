"""Controlled stdio peer used only by the transport checker's subprocess tests.

Examples:
    ```python
    from tests.unit.mcp_smoke_peer import tool_answer

    tool_answer("ask_noul")["structuredContent"]["noul"]
    ```

See Also:
    - [scripts.mcp_smoke_transport][]: Checker that owns this child.
"""

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

NAMES = ["ask_noul", "ask_choice", "ask_score"]


def tool_answer(name: str) -> dict[str, Any]:
    """Return a valid tool frame's result for a named fixture tool.

    Args:
        name: Tool name.

    Returns:
        Structured tool answer.
    """
    answers: dict[str, dict[str, Any]] = {
        "ask_noul": {"noul": 0.42},
        "ask_choice": {
            "choice": "yes",
            "confidence": 0.8,
            "probabilities": {"yes": 0.8, "no": 0.2},
        },
        "ask_score": {
            "score": 1.5,
            "confidence": 0.6,
            "legend": {"0": "Poor", "1": "Fair", "2": "Good", "3": "Excellent"},
            "probabilities": {"0": 0.1, "1": 0.4, "2": 0.4, "3": 0.1},
        },
    }
    return {
        "structuredContent": {
            **answers[name],
            "model": "fixture-model",
            "usage": {"input_tokens": 3, "output_tokens": 2},
        },
        "isError": False,
        "content": [],
    }


def result_for(request: dict[str, Any], version: str) -> dict[str, Any]:
    """Produce a result after enforcing the required initialization fields.

    Args:
        request: Incoming request.
        version: Advertised fixture version.

    Returns:
        Result payload.
    """
    if request["method"] == "initialize":
        assert request["params"]["protocolVersion"] == "2025-03-26"
        assert request["params"]["clientInfo"]["name"] == "judgevet-smoke"
        return {
            "serverInfo": {"name": "judgevet-mcp", "version": version},
            "protocolVersion": "2025-03-26",
            "capabilities": {},
        }
    if request["method"] == "tools/list":
        return {"tools": [{"name": name} for name in NAMES]}
    return tool_answer(request["params"]["name"])


def damage(result: dict[str, Any], mode: str) -> None:
    """Inject one defect when its relevant response arrives.

    Args:
        result: Mutable result payload.
        mode: Defect to inject.
    """
    if "serverInfo" in result and mode == "stale_version":
        result["serverInfo"]["version"] = "stale"
    if "tools" in result:
        if mode == "missing_tool":
            result["tools"].pop()
        elif mode == "duplicate_tool":
            result["tools"][-1] = result["tools"][0]
    damage_answer(result, mode)
    damage_extra(result, mode)


def damage_answer(result: dict[str, Any], mode: str) -> None:
    """Inject malformed typed content into a tool result.

    Args:
        result: Mutable result payload.
        mode: Defect to inject.
    """
    if "structuredContent" not in result:
        return
    answer = result["structuredContent"]
    if mode == "tool_error":
        result["isError"] = True
    elif mode == "bad_shape":
        result["structuredContent"] = []
    elif mode == "bad_usage":
        answer["usage"]["input_tokens"] = True
    elif mode == "empty_model":
        answer["model"] = ""
    elif "noul" in answer and mode in {"bool_number", "nan_number"}:
        answer["noul"] = True if mode == "bool_number" else float("nan")
    elif "choice" in answer and mode == "bad_distribution":
        answer["probabilities"] = {"yes": 0.2, "no": 0.2}
    elif "score" in answer and mode == "bad_legend":
        answer["legend"]["0"] = "Incorrect"


def damage_extra(result: dict[str, Any], mode: str) -> None:
    """Inject boundary values omitted by the initial test draft.

    Args:
        result: Mutable result payload.
        mode: Defect or valid edge case.
    """
    answer = result.get("structuredContent")
    if not isinstance(answer, dict):
        return
    if mode == "omit_error":
        result.pop("isError", None)
    if mode == "is_error_string":
        result["isError"] = "false"
    if "noul" in answer and mode == "huge_number":
        answer["noul"] = 10**400
    distributions = {
        "negative_probability": {"yes": -1.0, "no": 2.0},
        "nan_probability": {"yes": float("nan"), "no": 0.0},
        "bool_probability": {"yes": True, "no": 0.0},
        "integer_probability": {"yes": 1, "no": 0},
    }
    if "choice" in answer and mode in distributions:
        answer["probabilities"] = distributions[mode]


def emit(response: dict[str, Any], mode: str) -> None:
    """Emit a frame with optional envelope or encoding defects.

    Args:
        response: Response envelope.
        mode: Defect to inject.
    """
    if mode == "bool_id" and response["id"] == 1:
        response["id"] = True
    if mode == "extra_method":
        response["method"] = "notifications/unexpected"
    response["extra"] = "canary-placeholder"
    encoded = json.dumps(response).encode()
    if mode == "invalid_utf8":
        encoded = encoded.replace(b"canary-placeholder", b"\xff")
    if mode == "missing_newline" and response["id"] == 5:
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
        sys.exit(0)
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


def serve(mode: str, version: str) -> None:
    """Answer requests while exposing a selected protocol defect.

    Args:
        mode: Defect name or success.
        version: Advertised version.
    """
    initialized = False
    for line in sys.stdin:
        request = json.loads(line)
        if request["method"] == "notifications/initialized":
            initialized = True
            continue
        if request["method"] != "initialize":
            assert initialized
        if mode == "early_eof":
            return
        if mode == "malformed":
            print("canary-output not JSON", flush=True)
            return
        result = result_for(request, version)
        damage(result, mode)
        response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        if mode == "wrong_id":
            response["id"] = 999
        emit(response, mode)
    if mode == "trailing_noise":
        print("canary-output trailing", flush=True)
    if mode == "stalled_exit":
        time.sleep(60)
    if mode == "nonzero_exit":
        sys.exit(7)


def main() -> None:
    """Record this child's PID and run the selected fixture mode."""
    mode, pid_file, version = sys.argv[1:]
    Path(pid_file).write_text(str(os.getpid()))
    if mode == "stalled_exit":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if mode == "stalled_handshake":
        time.sleep(60)
    if mode == "stdout_flood":
        os.write(1, b"canary-output" * 100_000)
    if mode == "stderr_pressure":
        os.write(2, b"canary-output" * 100_000)
    serve(mode, version)


if __name__ == "__main__":
    main()
