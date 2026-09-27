"""An application MCP server built on the installed stdio entry point (#205).

Usage: ``python -m tests.fixtures.providers.mcp_app MODE``. ``owned`` serves
an owned factory; ``text-only`` serves a borrowed provider without media
support. Protocol frames use stdout; fixture events go to the events file.
"""

import sys
from functools import partial

from judgevet.adapters.inbound.mcp_entrypoint import main as serve
from tests.fixtures.providers.provider_fixture import (
    REQUESTED_MODEL,
    TextOnlyProvider,
    owned,
    record,
)


def main(argv: list[str]) -> int:
    """Serve MCP stdio with the selected provider and host-selected model.

    Args:
        argv: One mode argument.

    Returns:
        The entry point's exit status.
    """
    if argv[0] == "text-only":
        provider = TextOnlyProvider("text-only-mcp")
        code = serve(port=provider, model=REQUESTED_MODEL)
        record({"event": "borrowed-exit", "closed": provider.inner.closed})
        return code
    return serve(provider_factory=partial(owned, "owned-mcp"), model=REQUESTED_MODEL)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
