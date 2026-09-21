# Jev Client API Reference

> **status: draft.** The success response and the 401/422 error bodies are
> verified against the live service (2026-09-21). The 429 and 529 bodies,
> models other than `jev-1.13.0`, and any field no call has exercised remain
> inferred from published documentation. `STATUS.md` holds the line-by-line
> table.

## Question Types

### Noul

A yes/no question.

**Parameters:**
- `instructions`: The yes/no question or statement to evaluate
- `criteria`: Optional. An object with `true` and `false` descriptions of what a yes and a no mean. See: https://docs.typesafe.ai/primitives/noul

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
- `transport`: Optional httpx transport for testing (default: `None`)

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
from judgevet import HTTPSystemOneAdapter, Noul, Choice

adapter = HTTPSystemOneAdapter()

response = adapter.system_one(
    state="I was charged twice for my plan",
    questions={
        "is_refund": Noul(instructions="Is this about a refund?"),
        "queue": Choice(
            criteria={"a": "Option A", "b": "Option B"},
            instructions="Choose one:",
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
