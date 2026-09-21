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

Attributes:
    __version__ (str): The installed package version. release-please
        rewrites this line on every release. Do not edit it by hand.
    Choice (type): Question type for selecting one option from a set.
    HTTPSystemOneAdapter (type): HTTP adapter for the Jev API.
    Noul (type): Question type for yes/no questions.
    Score (type): Question type for rating on an ordered scale.

See Also:
    - [judgevet.adapters.outbound.http.HTTPSystemOneAdapter][]: HTTP adapter
    - [judgevet.domain.questions.Choice][]: Choice question type
    - [judgevet.domain.questions.Noul][]: Noul question type
    - [judgevet.domain.questions.Score][]: Score question type
    - https://docs.typesafe.ai/: Official TypeSafe documentation
    - https://docs.typesafe.ai/introduction.md: Introduction to Jev
"""

from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.questions import Choice, Noul, Score

__version__ = "0.1.0"  # x-release-please-version

__all__ = ["Choice", "HTTPSystemOneAdapter", "Noul", "Score", "__version__"]
