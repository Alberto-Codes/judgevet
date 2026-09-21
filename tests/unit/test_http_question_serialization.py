"""Unit tests for Question object to wire dict conversion in HTTP adapters."""

from __future__ import annotations

import json
from typing import Any

import anyio
import httpx

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.questions import Choice, Noul, Score


class TestHTTPSystemOneQuestionSerialization:
    """Tests for Question object serialization in HTTPSystemOneAdapter."""

    def test_system_one_serializes_question_types(self) -> None:
        """Test that Question objects are converted to wire dicts.

        This test drives the adapter with MockTransport to capture the actual
        request JSON. Every existing test passed dicts, so this is the first
        test that exercises the wire boundary with a Question object.
        """
        captured_requests: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = request.read().decode("utf-8")
            captured_requests.append(json.loads(body))
            return httpx.Response(
                200,
                json={
                    "model": "jev-1.13.0",
                    "answers": {},
                    "usage": {"input_tokens": 10, "output_tokens": 0},
                },
            )

        adapter = HTTPSystemOneAdapter(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )

        noul_no_criteria = Noul(instructions="Is this valid?")
        noul_with_criteria = Noul(
            instructions="Is this correct?",
            criteria={"yes": "Correct", "no": "Incorrect"},
        )
        choice = Choice(
            criteria={"a": "Option A", "b": "Option B"},
            instructions="Choose one:",
        )
        score = Score(
            criteria=["Poor", "Fair", "Good", "Excellent"],
            instructions="Rate quality:",
        )

        adapter.system_one(
            state="Test content",
            questions={
                "bare_noul": noul_no_criteria,
                "noul": noul_with_criteria,
                "choice": choice,
                "score": score,
            },
        )

        assert len(captured_requests) == 1
        questions = captured_requests[0]["questions"]

        # Bare Noul without criteria
        assert questions["bare_noul"] == {
            "type": "noul",
            "instructions": "Is this valid?",
        }

        # Noul with criteria
        assert questions["noul"] == {
            "type": "noul",
            "instructions": "Is this correct?",
            "criteria": {"yes": "Correct", "no": "Incorrect"},
        }

        # Choice with criteria
        assert questions["choice"] == {
            "type": "choice",
            "instructions": "Choose one:",
            "criteria": {"a": "Option A", "b": "Option B"},
        }

        # Score with criteria (note: criteria is a list, not dict)
        assert questions["score"] == {
            "type": "score",
            "instructions": "Rate quality:",
            "criteria": ["Poor", "Fair", "Good", "Excellent"],
        }

    def test_system_one_mixed_mapping(self) -> None:
        """Test that mixed Question objects and raw dicts work together."""
        captured_requests: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = request.read().decode("utf-8")
            captured_requests.append(json.loads(body))
            return httpx.Response(
                200,
                json={
                    "model": "jev-1.13.0",
                    "answers": {},
                    "usage": {"input_tokens": 10, "output_tokens": 0},
                },
            )

        adapter = HTTPSystemOneAdapter(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )

        adapter.system_one(
            state="Test content",
            questions={
                "obj": Noul(instructions="From object"),
                "dict": {
                    "type": "choice",
                    "instructions": "From dict",
                    "criteria": {"x": "X", "y": "Y"},
                },
            },
        )

        assert len(captured_requests) == 1
        questions = captured_requests[0]["questions"]

        assert questions["obj"] == {
            "type": "noul",
            "instructions": "From object",
        }
        assert questions["dict"] == {
            "type": "choice",
            "instructions": "From dict",
            "criteria": {"x": "X", "y": "Y"},
        }


class TestAsyncHTTPSystemOneQuestionSerialization:
    """The async twin of the suite above.

    The conversion lives in ``_build_payload``, which both adapters call, so
    one change covers both — and that is exactly why the async side needs its
    own test. A shared helper means a regression appears in both adapters at
    once, and a suite that only exercises the sync path would report a single
    failure for a defect that reaches every caller.
    """

    def test_system_one_serializes_question_types(self) -> None:
        """Question objects convert to wire dicts on the async path too.

        Driven with ``anyio.run`` from a sync test function, the pattern the
        other async suites in this repo use. No pytest-asyncio.
        """
        captured_requests: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(json.loads(request.read().decode("utf-8")))
            return httpx.Response(
                200,
                json={
                    "model": "jev-1.13.0",
                    "answers": {},
                    "usage": {"input_tokens": 10, "output_tokens": 0},
                },
            )

        async def drive() -> None:
            async with AsyncHTTPSystemOneAdapter(
                api_key="test-key",
                transport=httpx.MockTransport(handler),
            ) as adapter:
                await adapter.system_one(
                    state="Test content",
                    questions={
                        "bare_noul": Noul(instructions="Is this valid?"),
                        "choice": Choice(
                            criteria={"a": "Option A", "b": "Option B"},
                            instructions="Choose one:",
                        ),
                        "score": Score(
                            criteria=["Poor", "Fair", "Good", "Excellent"],
                            instructions="Rate quality:",
                        ),
                        "raw_dict": {"type": "noul", "instructions": "Already a dict"},
                    },
                )

        anyio.run(drive)

        assert len(captured_requests) == 1
        sent = captured_requests[0]["questions"]

        # The bare Noul is the package docstring's own example, and the one
        # case no live call had ever sent: criteria is None and must be
        # omitted rather than serialised as null.
        assert sent["bare_noul"] == {"type": "noul", "instructions": "Is this valid?"}
        assert "criteria" not in sent["bare_noul"]

        # score takes a list where noul and choice take a dict.
        assert sent["choice"] == {
            "type": "choice",
            "instructions": "Choose one:",
            "criteria": {"a": "Option A", "b": "Option B"},
        }
        assert sent["score"] == {
            "type": "score",
            "instructions": "Rate quality:",
            "criteria": ["Poor", "Fair", "Good", "Excellent"],
        }

        # A value that is already a dict passes through untouched.
        assert sent["raw_dict"] == {"type": "noul", "instructions": "Already a dict"}
