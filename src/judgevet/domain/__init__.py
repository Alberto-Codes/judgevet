"""Domain layer - pure types and business logic.

Examples:
    ```python
    from judgevet.domain import Noul, Choice, Score
    from judgevet.domain.answers import NoulAnswer, ChoiceAnswer, ScoreAnswer

    # Create a yes/no question
    noul = Noul(
        instructions="Is this a valid question?",
        criteria={"true": "It is valid", "false": "It is not valid"},
    )

    # Create a choice question
    choice = Choice(
        criteria={"a": "Option A", "b": "Option B"},
        instructions="Choose one:",
    )

    # Create a score question
    score = Score(
        criteria=["Poor", "Fair", "Good", "Excellent"],
        instructions="Rate the response:",
    )

    # Answer a question
    answer = NoulAnswer(noul=0.75)
    assert 0.0 <= answer.noul <= 1.0
    ```

See Also:
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.errors][]: Error types
    - [judgevet.domain.questions][]: Question types
    - [judgevet.domain.response][]: Response container
    - [judgevet.domain.usage][]: Usage tracking

Attributes:
    Answer (type): Union type of all answer types.
    Choice (type): Question type for multiple choice.
    ChoiceAnswer (type): Answer type for multiple choice.
    JevAuthError (type): 401/403 authentication errors.
    JevBudgetExceededError (type): Local spend cap refused an attempt.
    JevError (type): Base exception for all Jev errors.
    JevMaxTokensExceededError (type): Request over a service token budget.
    JevRateLimitError (type): 429 rate limit errors.
    JevRequestError (type): 4xx client request errors.
    JevResponseError (type): 2xx with unparseable body.
    JevServiceError (type): 5xx or transport errors.
    Noul (type): Question type for yes/no.
    NoulAnswer (type): Answer type for yes/no.
    Question (type): Base question type.
    Score (type): Question type for numeric rating.
    ScoreAnswer (type): Answer type for numeric rating.
    SystemOneResponse (type): API response container.
    Usage (type): API usage tracking.
"""

from judgevet.domain.answers import (
    Answer,
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from judgevet.domain.errors import (
    JevAuthError,
    JevBudgetExceededError,
    JevError,
    JevMaxTokensExceededError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage

__all__ = [
    "Answer",
    "Choice",
    "ChoiceAnswer",
    "JevAuthError",
    "JevBudgetExceededError",
    "JevError",
    "JevMaxTokensExceededError",
    "JevRateLimitError",
    "JevRequestError",
    "JevResponseError",
    "JevServiceError",
    "Noul",
    "NoulAnswer",
    "Question",
    "Score",
    "ScoreAnswer",
    "SystemOneResponse",
    "Usage",
]
