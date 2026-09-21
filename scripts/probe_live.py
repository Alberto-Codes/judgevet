#!/usr/bin/env python3
"""Print one real Jev response, so the domain model can be checked against it.

Every field name in this repo came from reading documentation. The live test
proved a call succeeds; it did not show what came back, because its assertions
ran over a raw dict. This prints the body.

It is a probe, not a test. It makes one paid call, writes what it got, and
asserts nothing. Use it when the domain model needs to be reconciled with the
service (#17, #6), then read the output rather than trusting the model.

The API key is never printed.

Usage:
    direnv exec . uv run python scripts/probe_live.py
    direnv exec . uv run python scripts/probe_live.py --out probe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter

QUESTIONS = {
    "is_urgent": {
        "type": "noul",
        "instructions": "Does this convey urgency?",
    },
    "department": {
        "type": "choice",
        "instructions": "Which team must handle this?",
        "criteria": {
            "billing": "Payments, invoicing, and refunds",
            "technical": "Bugs, outages, and integrations",
        },
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": ["Calm", "Frustrated", "Very angry"],
    },
}

STATE = "Help! My payouts have been failing for 3 days."


def main() -> int:
    """Make one call and print the raw response.

    Returns:
        1 when no API key is configured, 0 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Also write the body to this file.")
    args = parser.parse_args()

    settings = Settings()
    if settings.api.key is None:
        print("No API key. Set TYPESAFE_API_KEY (see .envrc).", file=sys.stderr)
        return 1

    adapter = HTTPSystemOneAdapter(
        api_key=settings.api.key.get_secret_value(),
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
    )
    try:
        body = adapter.system_one(
            state=STATE, questions=QUESTIONS, model=settings.api.default_model
        )
    finally:
        adapter.close()

    rendered = json.dumps(body, indent=2, sort_keys=True)
    print(rendered)
    if args.out:
        args.out.write_text(rendered + "\n")
        print(f"\nwritten to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
