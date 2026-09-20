# Jev Client API Reference

## Question Types

### Noul

A yes/no question.

**Parameters:**
- `instructions`: The yes/no question or statement to evaluate
- `criteria`: Optional descriptions of the yes and no outcomes

**Response:** `NoulAnswer` with `noul` probability (0-1)

### Choice

A question that selects between named alternatives.

**Parameters:**
- `criteria`: Labels mapped to descriptions
- `instructions`: The question to ask

**Response:** `ChoiceAnswer` with `choice` name, `confidence`, and `probabilities`

### Score

A question that assigns a score using an ordered rubric.

**Parameters:**
- `criteria`: Ordered list of descriptions (position = score level)
- `instructions`: What the model should rate

**Response:** `ScoreAnswer` with `score`, `confidence`, `legend`, and `probabilities`

## Adapters

### HTTPSystemOneAdapter

HTTP implementation of the SystemOnePort.

**Parameters:**
- `api_key`: TypeSafe API key (or `TYPESAFE_API_KEY` env var)
- `base_url`: API base URL (default: `https://api.typesafe.ai`)
- `default_model`: Default model (default: `jev-latest`)

**Methods:**
- `system_one(state, questions, model)`: Call the Jev API
- `close()`: Close the HTTP client

## Domain Types

### NoulAnswer

Yes/no answer.

**Attributes:**
- `noul`: Probability of yes/true (0-1)

### ChoiceAnswer

Selected choice with probabilities.

**Attributes:**
- `choice`: The selected label
- `confidence`: Confidence in the choice (0-1)
- `probabilities`: Probability per choice

### ScoreAnswer

Scored response.

**Attributes:**
- `score`: Expected score
- `confidence`: Confidence in the score (0-1)
- `legend`: Rubric descriptions keyed by score level
- `probabilities`: Probability per score level

### Usage

Token counts.

**Attributes:**
- `input_tokens`: Billable input tokens
- `output_tokens`: Output tokens (currently free)

## Examples

### Basic Usage

```python
from jev_client import HTTPSystemOneAdapter, Noul, Choice

adapter = HTTPSystemOneAdapter()

response = adapter.system_one(
    state="I was charged twice for my plan",
    questions={
        "is_refund": Noul(instructions="Is this about a refund?"),
        "queue": Choice(
            criteria={
                "billing": "Money issues",
                "technical": "Bugs",
            },
            instructions="Which team handles this?",
        ),
    },
)

assert 0 <= response.answers["is_refund"].noul <= 1
assert response.answers["queue"].choice in {"billing", "technical"}
```

### Context Manager

```python
with HTTPSystemOneAdapter() as adapter:
    response = adapter.system_one(
        state="Test",
        questions={},
        model="jev-1.13.0",
    )
```
