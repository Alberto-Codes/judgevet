"""Report what a judgevet install without the conformance extra offers (#241).

The fakes in ``judgevet.testing`` must import without pytest, and importing
``judgevet.testing.conformance`` must raise an ``ImportError`` that names the
``judgevet[conformance]`` extra. The runner starts this module through the
network-guarding bootstrap and compares the printed receipt with its oracle.
"""

import importlib
import importlib.util
import json
from typing import Any


def observe() -> dict[str, Any]:
    """Import the fakes, then attempt the conformance kit.

    Returns:
        The absence receipt.
    """
    fakes = importlib.import_module("judgevet.testing")
    receipt: dict[str, Any] = {
        "receipt": "conformance-absent",
        "fakes": fakes.FakeSystemOnePort.__name__,
        "pytest": importlib.util.find_spec("pytest") is not None,
    }
    try:
        importlib.import_module("judgevet.testing.conformance")
    except ImportError as error:
        receipt["error"] = type(error).__name__
        receipt["extra_named"] = "judgevet[conformance]" in str(error)
    else:
        receipt["error"] = None
        receipt["extra_named"] = False
    return receipt


if __name__ == "__main__":
    print(json.dumps(observe()))
