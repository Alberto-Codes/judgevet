"""Jev (TypeSafe System One) Python client.

This client provides typed access to TypeSafe's Jev API, which answers
structured questions about text with calibrated confidence values.

Examples:
    ```python
    from jev_client import Choice, HTTPSystemOneAdapter, Noul, Score

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
    Choice (type): Question type for selecting one option from a set.
    HTTPSystemOneAdapter (type): HTTP adapter for the Jev API.
    Noul (type): Question type for yes/no questions.
    Score (type): Question type for rating on an ordered scale.

See Also:
    - [jev_client.adapters.outbound.http.HTTPSystemOneAdapter][]: HTTP adapter
    - [jev_client.domain.questions.Choice][]: Choice question type
    - [jev_client.domain.questions.Noul][]: Noul question type
    - [jev_client.domain.questions.Score][]: Score question type
    - https://docs.typesafe.ai/: Official TypeSafe documentation
    - https://docs.typesafe.ai/introduction.md: Introduction to Jev
"""

from jev_client.adapters.outbound.http import HTTPSystemOneAdapter
from jev_client.domain.questions import Choice, Noul, Score

__all__ = ["Choice", "HTTPSystemOneAdapter", "Noul", "Score"]
