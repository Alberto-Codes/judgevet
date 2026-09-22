"""Jev (TypeSafe System One) Python client.

This client provides typed access to TypeSafe's Jev API, which answers
structured questions about text with calibrated confidence values.

Examples:
    ```python
    from judgevet import Choice, HTTPSystemOneAdapter, Noul, Score

    adapter = HTTPSystemOneAdapter(api_key="your-api-key")
    try:
        response = adapter.system_one(
            state="Test content",
            questions={
                "q1": Noul(instructions="Is this valid?"),
                "q2": Choice(
                    criteria={"a": "Option A", "b": "Option B"},
                    instructions="Choose one",
                ),
            },
        )
        print(response.answers)
    finally:
        adapter.close()
    ```

    The async adapter is the same call, awaited. It is a separate class
    rather than a mode, because the sync and async methods share a name and
    a Protocol's members are keyed by name — the two cannot live behind one
    port:

    ```python
    from judgevet import AsyncHTTPSystemOneAdapter, Noul

    async with AsyncHTTPSystemOneAdapter(api_key="your-api-key") as adapter:
        response = await adapter.system_one(
            state="Test content",
            questions={"q1": Noul(instructions="Is this valid?")},
        )
    ```

    It has no `close`, `__enter__` or `__exit__`; those raise
    `AttributeError` on purpose, because a synchronous close would return an
    un-awaited coroutine and close nothing.

Attributes:
    __version__ (str): The installed package version. release-please
        rewrites this line on every release. Do not edit it by hand.
    AsyncHTTPSystemOneAdapter (type): Async HTTP adapter for the Jev API,
        proven to agree with the sync one on the contract fixtures.
    Choice (type): Question type for selecting one option from a set.
    HTTPSystemOneAdapter (type): HTTP adapter for the Jev API.
    Noul (type): Question type for yes/no questions.
    Score (type): Question type for rating on an ordered scale.

See Also:
    - [judgevet.adapters.outbound.http.AsyncHTTPSystemOneAdapter][]: async HTTP adapter
    - [judgevet.adapters.outbound.http.HTTPSystemOneAdapter][]: HTTP adapter
    - [judgevet.domain.questions.Choice][]: Choice question type
    - [judgevet.domain.questions.Noul][]: Noul question type
    - [judgevet.domain.questions.Score][]: Score question type
    - https://docs.typesafe.ai/: Official TypeSafe documentation
    - https://docs.typesafe.ai/introduction.md: Introduction to Jev
"""

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.questions import Choice, Noul, Score

__version__ = "0.5.0"  # x-release-please-version

__all__ = [
    "AsyncHTTPSystemOneAdapter",
    "Choice",
    "HTTPSystemOneAdapter",
    "Noul",
    "Score",
    "__version__",
]
