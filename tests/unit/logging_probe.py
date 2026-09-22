"""Run isolated HTTP calls for real-stream logging acceptance.

Examples:
    ```bash
    uv run python -m tests.unit.logging_probe sync success
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Adapters under test.
"""

import asyncio
import sys

import httpx

from judgevet.adapters.inbound.logs import LogSettings, configure
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevError
from tests.cli_process_support import SUCCESS

CANARY = "private-logging-canary"


def main() -> None:
    """Exercise one configured or silent adapter call without printing payloads."""
    mode, outcome = sys.argv[1:3]
    if len(sys.argv) == 3:
        configure(LogSettings(level="debug", format="json"))

    def respond(request: httpx.Request) -> httpx.Response:
        if outcome == "transport":
            raise httpx.ConnectError(CANARY, request=request)
        if outcome == "parse":
            return httpx.Response(200, json={"input": CANARY})
        if outcome == "success":
            return httpx.Response(200, json=SUCCESS)
        return httpx.Response(int(outcome), json={"detail": {"message": CANARY}})

    transport = httpx.MockTransport(respond)
    questions = {CANARY: {"type": "noul", "instructions": CANARY}}

    async def call() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key=CANARY, transport=transport
        ) as port:
            await port.system_one(CANARY, questions, "jev-latest")

    try:
        if mode == "async":
            asyncio.run(call())
        else:
            with HTTPSystemOneAdapter(api_key=CANARY, transport=transport) as port:
                port.system_one(CANARY, questions, "jev-latest")
    except JevError:
        pass


if __name__ == "__main__":
    main()
