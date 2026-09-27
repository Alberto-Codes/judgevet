"""An application CLI built on the installed ``create_cli_app`` factory (#205).

Usage: ``python -m tests.fixtures.providers.cli_app MODE [judgevet options]``.
``MODE`` selects a borrowed provider, an owned factory, a failing owned
factory or a borrowed text-only provider. The remaining arguments go to the
installed command unchanged. Fixture events go to the events file only.
"""

import sys
from functools import partial

from judgevet.adapters.inbound.cli import create_cli_app
from tests.fixtures.providers.provider_fixture import (
    RecordingProvider,
    TextOnlyProvider,
    owned,
    record,
)


def main(argv: list[str]) -> int:
    """Run the installed command with the selected provider.

    Args:
        argv: Mode followed by command arguments.

    Returns:
        The command's exit status.
    """
    mode, arguments = argv[0], argv[1:]
    borrowed: RecordingProvider | None = None
    if mode == "borrowed":
        borrowed = RecordingProvider("borrowed-cli")
        application = create_cli_app(port=borrowed)
    elif mode == "text-only":
        text_only = TextOnlyProvider("text-only-cli")
        borrowed = text_only.inner
        application = create_cli_app(port=text_only)
    elif mode == "owned":
        application = create_cli_app(provider_factory=partial(owned, "owned-cli"))
    else:
        factory = partial(owned, "failing-cli", fail=True)
        application = create_cli_app(provider_factory=factory)
    try:
        application(arguments, prog_name="fixture-cli")
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else 1
    else:
        code = 0
    if borrowed is not None:
        record({"event": "borrowed-exit", "closed": borrowed.closed})
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
