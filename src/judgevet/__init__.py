"""Jev (TypeSafe System One) Python client.

This client provides typed access to TypeSafe's Jev API, which answers
structured questions about supplied content. Returned confidence values do not
establish calibration for a caller's task.

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

    The async adapter is the same call, awaited. It uses a separate class
    because the sync and async methods share a name. A Protocol's members are
    keyed by name, so the two cannot live behind one port:

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

The root exports domain types, errors, ports and scoped diagnostic correlation.
Existing deep imports retain object identity. Callers own adapter construction
and cleanup; importing a port does not create a client.

Attributes:
    bind_request_id (Callable): Context manager for local caller correlation.
    Answer (type): Union of the three typed answers.
    Question (type): Union of the three typed questions.
    SystemOnePort (type): Synchronous structural port protocol.
    AsyncSystemOnePort (type): Asynchronous structural port protocol.
    NoulAnswer (type): Typed Noul answer.
    ChoiceAnswer (type): Typed Choice answer.
    ScoreAnswer (type): Typed Score answer.
    SystemOneResponse (type): Answer container with typed accessors.
    Usage (type): Token usage metadata.
    RetryPolicy (type): Immutable opt-in retry limits.
    NetworkConfig (type): Explicit proxy and certificate verification options.
    JevError (type): Base Jev exception.
    JevAuthError (type): Authentication failure.
    JevRequestError (type): Rejected request.
    JevResponseError (type): Unparseable successful answer body.
    JevServiceError (type): Service or transport failure.
    JevRateLimitError (type): Rate limit failure.
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
from judgevet.adapters.outbound.network import NetworkConfig
from judgevet.adapters.outbound.retries import RetryPolicy
from judgevet.diagnostics import bind_request_id
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.ports import AsyncSystemOnePort, SystemOnePort

__version__ = "0.7.0"  # x-release-please-version

__all__ = [
    "Answer",
    "AsyncHTTPSystemOneAdapter",
    "AsyncSystemOnePort",
    "Choice",
    "ChoiceAnswer",
    "HTTPSystemOneAdapter",
    "JevAuthError",
    "JevError",
    "JevRateLimitError",
    "JevRequestError",
    "JevResponseError",
    "JevServiceError",
    "NetworkConfig",
    "Noul",
    "NoulAnswer",
    "Question",
    "RetryPolicy",
    "Score",
    "ScoreAnswer",
    "SystemOnePort",
    "SystemOneResponse",
    "Usage",
    "__version__",
    "bind_request_id",
]
