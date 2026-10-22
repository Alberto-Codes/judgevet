"""Redirect tutorial HTTPX2 clients to the executor's synthetic loopback service.

Examples:
    Run through the parent, which prepares the isolated environment:

    ```bash
    uv run python -m scripts.check_doc_python
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Adapter exercised without changing examples.
"""

import os
from typing import Any
from unittest.mock import patch

import httpx2


class FixtureClient(httpx2.Client):
    """Use the fixture endpoint while retaining real adapter serialization.

    Attributes:
        base_url: Loopback endpoint supplied by the isolated shell executor.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Select the controlled endpoint before constructing the HTTP client.

        Args:
            kwargs: Original HTTPX2 constructor arguments from the adapter.
        """
        kwargs["base_url"] = os.environ["JEV_API__BASE_URL"]
        super().__init__(**kwargs)


_client_patch = patch.object(httpx2, "Client", FixtureClient)
_client_patch.start()
