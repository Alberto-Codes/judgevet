"""Contract test fixtures.

Each fixture represents a single HTTP interaction with the Jev System One API.

All success body fixtures are **inferred** from docs/reference/api.md, not
recorded from the live service. Every field name is cited to that page.

See: https://docs.typesafe.ai/api.md
"""

from __future__ import annotations

from typing import Any


def _make_noul_fixture() -> dict[str, Any]:
    """Fixture 1: One noul answer."""
    return {
        "name": "noul_success",
        "request": {
            "state": "I was charged twice for my plan",
            "questions": {
                "is_refund": {
                    "type": "noul",
                    "instructions": "Is this about a refund?",
                }
            },
            "model": "jev-1.13.0",
        },
        "status": 200,
        "body": {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {
                "is_refund": {"type": "noul", "noul": 0.75},
            },
        },
        "expect": (
            "response",
            {
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 100, "output_tokens": 10},
                "answers": {
                    "is_refund": {"answer_type": "noul", "noul": 0.75},
                },
            },
        ),
    }


def _make_choice_fixture() -> dict[str, Any]:
    """Fixture 2: One choice answer."""
    return {
        "name": "choice_success",
        "request": {
            "state": "My credit card was declined",
            "questions": {
                "queue": {
                    "type": "choice",
                    "instructions": "Which team handles this?",
                    "criteria": {"billing": "Money issues", "technical": "Bugs"},
                }
            },
            "model": "jev-1.13.0",
        },
        "status": 200,
        "body": {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 120, "output_tokens": 12},
            "answers": {
                "queue": {
                    "type": "choice",
                    "choice": "billing",
                    "confidence": 0.8,
                    "probabilities": {"billing": 0.8, "technical": 0.2},
                }
            },
        },
        "expect": (
            "response",
            {
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 120, "output_tokens": 12},
                "answers": {
                    "queue": {
                        "answer_type": "choice",
                        "choice": "billing",
                        "confidence": 0.8,
                        "probabilities": {"billing": 0.8, "technical": 0.2},
                    }
                },
            },
        ),
    }


def _make_score_fixture() -> dict[str, Any]:
    """Fixture 3: One score answer."""
    return {
        "name": "score_success",
        "request": {
            "state": "The product arrived damaged",
            "questions": {
                "satisfaction": {
                    "type": "score",
                    "instructions": "Rate your satisfaction",
                    "criteria": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                }
            },
            "model": "jev-1.13.0",
        },
        "status": 200,
        "body": {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 140, "output_tokens": 14},
            "answers": {
                "satisfaction": {
                    "type": "score",
                    "score": 2.5,
                    "confidence": 0.9,
                    "legend": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                    "probabilities": {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
                }
            },
        },
        "expect": (
            "response",
            {
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 140, "output_tokens": 14},
                "answers": {
                    "satisfaction": {
                        "answer_type": "score",
                        "score": 2.5,
                        "confidence": 0.9,
                        "legend": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                        "probabilities": {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
                    }
                },
            },
        ),
    }


def _make_mixed_request() -> dict[str, Any]:
    """Return the request part of fixture 4."""
    return {
        "state": "I was charged twice for my plan and my credit card was declined",
        "questions": {
            "is_refund": {
                "type": "noul",
                "instructions": "Is this about a refund?",
            },
            "queue": {
                "type": "choice",
                "instructions": "Which team handles this?",
                "criteria": {"billing": "Money issues", "technical": "Bugs"},
            },
            "satisfaction": {
                "type": "score",
                "instructions": "Rate your satisfaction",
                "criteria": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
            },
        },
        "model": "jev-1.13.0",
    }


def _make_mixed_body() -> dict[str, Any]:
    """Return the body part of fixture 4."""
    return {
        "model": "jev-1.13.0",
        "usage": {"input_tokens": 200, "output_tokens": 20},
        "answers": {
            "is_refund": {"type": "noul", "noul": 0.75},
            "queue": {
                "type": "choice",
                "choice": "billing",
                "confidence": 0.8,
                "probabilities": {"billing": 0.8, "technical": 0.2},
            },
            "satisfaction": {
                "type": "score",
                "score": 2.5,
                "confidence": 0.9,
                "legend": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                "probabilities": {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
            },
        },
    }


def _make_mixed_expect() -> tuple[str, dict[str, Any]]:
    """Return the expect part of fixture 4."""
    return (
        "response",
        {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 200, "output_tokens": 20},
            "answers": {
                "is_refund": {"answer_type": "noul", "noul": 0.75},
                "queue": {
                    "answer_type": "choice",
                    "choice": "billing",
                    "confidence": 0.8,
                    "probabilities": {"billing": 0.8, "technical": 0.2},
                },
                "satisfaction": {
                    "answer_type": "score",
                    "score": 2.5,
                    "confidence": 0.9,
                    "legend": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                    "probabilities": {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
                },
            },
        },
    )


def _make_mixed_fixture() -> dict[str, Any]:
    """Fixture 4: All three answers in one body."""
    return {
        "name": "mixed_success",
        "request": _make_mixed_request(),
        "status": 200,
        "body": _make_mixed_body(),
        "expect": _make_mixed_expect(),
    }


def _make_error_401_fixture() -> dict[str, Any]:
    """Fixture 5: 401 Unauthorized.

    Real body from live API on 2026-09-21:
    {"detail": {"error_type": "authentication_error",
                 "message": "Cannot authenticate with the server..."}}
    """
    return {
        "name": "error_401",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 401,
        "body": {
            "detail": {
                "error_type": "authentication_error",
                "message": "Cannot authenticate with the server...",
            }
        },
        "expect": ("error", "JevAuthError", 401),
    }


def _make_error_403_fixture() -> dict[str, Any]:
    """Fixture 6: 403 Forbidden."""
    return {
        "name": "error_403",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 403,
        "body": {},  # adapter never reads the body on non-2xx
        "expect": ("error", "JevAuthError", 403),
    }


def _make_error_429_fixture() -> dict[str, Any]:
    """Fixture 7: 429 Rate Limit."""
    return {
        "name": "error_429",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 429,
        "body": {},  # adapter never reads the body on non-2xx
        "expect": ("error", "JevRateLimitError", 429),
    }


def _make_error_422_fixture() -> dict[str, Any]:
    """Fixture 8: 422 Request Error.

    Real body from live API on 2026-09-21:
    {"detail": [{"type": "missing", "loc": ["body", "questions"],
                 "msg": "Field required",
                 "input": {"state": "x", "model": "jev-latest"}}]}
    """
    return {
        "name": "error_422",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 422,
        "body": {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "questions"],
                    "msg": "Field required",
                    "input": {"state": "x", "model": "jev-latest"},
                }
            ]
        },
        "expect": ("error", "JevRequestError", 422),
    }


def _make_error_500_fixture() -> dict[str, Any]:
    """Fixture 9: 500 Service Error."""
    return {
        "name": "error_500",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 500,
        "body": {},  # adapter never reads the body on non-2xx
        "expect": ("error", "JevServiceError", 500),
    }


def _make_transport_failure_fixture() -> dict[str, Any]:
    """Fixture 10: Transport failure."""
    return {
        "name": "transport_failure",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "raise_connect_error": True,
        "expect": ("error", "JevServiceError", None),
    }


def _make_missing_model_fixture() -> dict[str, Any]:
    """Fixture 11: 200 with missing model field."""
    return {
        "name": "missing_model_field",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 200,
        "body": {"usage": {"input_tokens": 100, "output_tokens": 10}, "answers": {}},
        "expect": ("error", "JevResponseError", 200),
    }


def _make_non_json_fixture() -> dict[str, Any]:
    """Fixture 12: 200 with non-JSON body."""
    return {
        "name": "non_json_body",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "raw_bytes": b"not json",
        "expect": ("error", "JevResponseError", 200),
    }


def _make_rounded_score_fixture() -> dict[str, Any]:
    """Fixture 13: A four-level score whose rounded probabilities sum to 0.99.

    One consumer call on 2026-09-24 (`jev-1.13.0`) returned a four-level Score
    with two-decimal probabilities that summed to 0.99. This body is synthetic;
    it reproduces that shape, not a recorded response.
    See: https://github.com/Alberto-Codes/judgevet/issues/175
    """
    legend = {1: "poor", 2: "fair", 3: "good", 4: "excellent"}
    probabilities = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.39}
    answer = {"score": 2.96, "confidence": 0.39, "legend": legend}
    return {
        "name": "score_rounded_sum",
        "request": {
            "state": "The product arrived damaged",
            "questions": {
                "satisfaction": {
                    "type": "score",
                    "instructions": "Rate your satisfaction",
                    "criteria": legend,
                }
            },
            "model": "jev-1.13.0",
        },
        "status": 200,
        "body": {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 140, "output_tokens": 14},
            "answers": {
                "satisfaction": {
                    "type": "score",
                    **answer,
                    "probabilities": probabilities,
                }
            },
        },
        "expect": (
            "response",
            {
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 140, "output_tokens": 14},
                "answers": {
                    "satisfaction": {
                        "answer_type": "score",
                        **answer,
                        "probabilities": probabilities,
                    }
                },
            },
        ),
    }


def _make_error_max_tokens_exceeded_fixture() -> dict[str, Any]:
    """Fixture 14: 400 with the oversized-payload marker.

    Real body from live API on 2026-09-25, `jev-1.13.0`, a 400,000-character
    state: {"detail": {"error_type": "max_tokens_exceeded"}}.
    The service sent it as `application/json`; the replay transport does too.
    See: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575

    Returns:
        The fixture mapping.
    """
    return {
        "name": "error_max_tokens_exceeded",
        "request": {"state": "test", "questions": {}, "model": "jev-1.13.0"},
        "status": 400,
        "body": {"detail": {"error_type": "max_tokens_exceeded"}},
        "expect": ("error", "JevMaxTokensExceededError", 400),
    }


def get_fixtures() -> list[dict[str, Any]]:
    """Return the list of all 14 fixtures."""
    return [
        _make_noul_fixture(),
        _make_choice_fixture(),
        _make_score_fixture(),
        _make_mixed_fixture(),
        _make_error_401_fixture(),
        _make_error_403_fixture(),
        _make_error_429_fixture(),
        _make_error_422_fixture(),
        _make_error_max_tokens_exceeded_fixture(),
        _make_error_500_fixture(),
        _make_transport_failure_fixture(),
        _make_missing_model_fixture(),
        _make_non_json_fixture(),
        _make_rounded_score_fixture(),
    ]


def get_fixture_by_name(name: str) -> dict[str, Any]:
    """Return a fixture by name."""
    for fixture in get_fixtures():
        if fixture["name"] == name:
            return fixture
    raise ValueError(f"Fixture not found: {name}")
