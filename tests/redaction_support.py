"""Supply explicit synthetic redactors and a typed call harness."""

import asyncio
from typing import Any

import httpx

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    GatewayConfig,
    HTTPSystemOneAdapter,
    RequestMetadata,
    RetryPolicy,
    StateRedactor,
)

State = str | dict[str, Any] | list[Any]


class SyntheticRedactor:
    """Mutate copied containers and replace only an explicit test sentinel."""

    def __init__(self) -> None:
        """Count calls and retain output to test retry ownership."""
        self.calls = 0
        self.output: State = ""

    def redact(self, state: State) -> State:
        """Transform an exact synthetic value; this is not a detection rule library."""
        self.calls += 1
        if isinstance(state, str):
            self.output = state.replace("state-canary", "removed")
        else:
            self._mutate(state)
            self.output = state
        return self.output

    def _mutate(self, value: dict[str, Any] | list[Any]) -> None:
        """Replace nested test values while preserving other synthetic content."""
        if isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = self._replacement(item)
        else:
            for key, item in value.items():
                value[key] = self._replacement(item)

    def _replacement(self, item: Any) -> Any:
        """Transform one synthetic item without losing its container type."""
        if isinstance(item, (dict, list)):
            self._mutate(item)
        elif item == "state-canary":
            return "removed"
        return item


def invoke(
    asynchronous: bool,
    redactor: StateRedactor | None,
    state: State,
    *,
    url: str,
    gateway: GatewayConfig | None = None,
    transport: httpx.MockTransport | None = None,
) -> None:
    """Run the same typed request through each concrete adapter."""
    metadata = RequestMetadata(headers={"Example-Explicit": "header-canary"})
    questions = {"q": {"type": "noul", "instructions": "question-canary"}}
    retry = RetryPolicy(3, 0, 0, True)
    if asynchronous:

        async def call() -> None:
            async with AsyncHTTPSystemOneAdapter(
                api_key="dummy",
                base_url=url,
                redactor=redactor,
                gateway=gateway,
                transport=transport,
                retry=retry,
            ) as adapter:
                await adapter.system_one(
                    state, questions, "jev-1.13.0", metadata=metadata
                )

        asyncio.run(call())
    else:
        with HTTPSystemOneAdapter(
            api_key="dummy",
            base_url=url,
            redactor=redactor,
            gateway=gateway,
            transport=transport,
            retry=retry,
        ) as adapter:
            adapter.system_one(state, questions, "jev-1.13.0", metadata=metadata)
