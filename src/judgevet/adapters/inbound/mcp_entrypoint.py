"""MCP stdio entry point for judgevet.

This module provides the composition root for the MCP stdio server.
The hosted path reads Settings once, configures stderr logging, builds the HTTP
adapter and serves stdio. ``JEV_API__AUDIT_PATH`` opens one audit sink first,
which closes after the adapter. Explicit provider selection bypasses hosted settings.
An application factory acquires and closes its provider on the dispatch worker.
Borrowed providers remain open when serving ends. A launcher may pass
replacement instructions, such as its own limits of use, in place of the
default server instructions. It may also pass an instructions addendum, which
follows them after a blank line. A fatal failure names its
stage and exception type names and omits exception text. A cleanup failure
after serving returns names the shutdown stage. When serving and cleanup both
fail, the serving stage names the serving types first, then the cleanup types.

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_entrypoint as entry

    assert callable(entry.main)
    ```

See Also:
    - [judgevet.adapters.inbound.settings][]: Settings for configuration
    - [judgevet.adapters.outbound.http][]: HTTP adapter
    - [judgevet.adapters.inbound.mcp][]: MCP server factory
    - [judgevet.ports][]: Port protocol

Attributes:
    __all__ (list): Public API exports.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from contextlib import nullcontext

from pydantic import ValidationError

from judgevet.adapters.inbound.logs import configure, configure_mcp_logging
from judgevet.adapters.inbound.mcp import create_mcp_server, server_instructions
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.audit_jsonl import JsonlAuditSink
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import JudgevetError
from judgevet.ports import AuditSink, SystemOnePort
from judgevet.providers import ProviderFactory

try:
    from mcp.server.stdio import stdio_server
except ModuleNotFoundError as exc:
    if exc.name == "mcp":
        stdio_server = None
    else:
        raise

__all__ = ["main"]


def build_adapter(
    settings: Settings, *, audit: AuditSink | None = None
) -> HTTPSystemOneAdapter:
    """Resolve one wrapped credential and apply host-selected gateway configuration.

    The spend cap is read once here, so it spans the server's lifetime and a
    tripped cap needs a restart.

    Args:
        settings: The Settings instance.
        audit: Open audit sink the caller owns and closes, or None.

    Returns:
        HTTPSystemOneAdapter configured with settings.

    Raises:
        ValueError: If credential resolution or connection configuration fails.
    """
    key = settings.api.resolve_key()
    return HTTPSystemOneAdapter(
        api_key=key.get_secret_value() if key is not None else None,
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
        timeout_seconds=settings.api.timeout_seconds,
        retry=settings.api.retry_policy,
        network=settings.api.network_config,
        gateway=settings.api.gateway_config,
        spend_cap=settings.api.spend_cap,
        audit=audit,
    )


def _options(
    instructions: str | None, addendum: str | None, **options: str
) -> dict[str, str]:
    """Add launcher instruction text to keyword options only when it is given.

    Args:
        instructions: Replacement server instructions, or None.
        addendum: Launcher instructions addendum, or None.

    Other Parameters:
        **options: Other keyword options to pass through.

    Returns:
        The options, with ``instructions`` and ``instructions_addendum`` when
        each is given.
    """
    if instructions is not None:
        options["instructions"] = instructions
    if addendum is not None:
        options["instructions_addendum"] = addendum
    return options


async def run_stdio(
    port: SystemOnePort,
    *,
    model: str = "jev-latest",
    instructions: str | None = None,
    instructions_addendum: str | None = None,
) -> None:
    """Run MCP stdio server with the given port.

    Args:
        port: The port used for API calls.
        model: Host-selected model.
        instructions: Text that replaces the default server instructions,
            or None.
        instructions_addendum: Text appended to the server instructions
            after a blank line, or None.

    Raises:
        RuntimeError: If MCP runtime is not available.
    """
    if stdio_server is None:
        raise RuntimeError("MCP runtime not available")
    options = {} if model == "jev-latest" else {"model": model}
    texts = _options(instructions, instructions_addendum, **options)
    server = create_mcp_server(port, **texts)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main(
    *,
    port: SystemOnePort | None = None,
    provider_factory: ProviderFactory | None = None,
    model: str = "jev-latest",
    instructions: str | None = None,
    instructions_addendum: str | None = None,
) -> int:
    """MCP stdio server entry point.

    The hosted path reads Settings once and owns its HTTP adapter. Explicit
    selection borrows a provider or enters an application factory context.
    Both paths configure logging and serve MCP with the host-selected model.

    Args:
        port: Borrowed application provider.
        provider_factory: Owning application factory.
        model: Host-selected model. On the hosted path, the default
            ``jev-latest`` defers to ``settings.api.default_model``.
        instructions: A consumer's own server instructions, such as its
            limits of use. They replace the default text. None sends the
            default text.
        instructions_addendum: Provider facts a self-hosted launcher appends
            to the server instructions after a blank line, such as which
            model answers. None sends the instructions alone.

    Returns:
        Exit code: 0 for success, 2 for configuration failures.

    Raises:
        ValueError: Both provider selection arguments are supplied.
        TypeError: The replacement instructions or the addendum is given
            and is not a str.
        SystemExit: If startup or serving raises a declared library error or an
            IO, runtime, value, type or grouped exception. The exit code is 1.
            The diagnostic reads ``judgevet-mcp: <stage> failed (<TypeName>)``.
            The stage is audit sink, credential resolution, provider
            acquisition, serving or shutdown. A group lists its distinct leaf type names.
            When cleanup fails after serving fails, the serving types come
            first, then the cleanup types, each distinct name once. Exception
            text and the cause chain are omitted.
    """
    if port is not None and provider_factory is not None:
        raise ValueError("Supply at most one of port or provider_factory")
    server_instructions(instructions_addendum, instructions=instructions)
    texts = _options(instructions, instructions_addendum)
    if stdio_server is None:
        print(
            "judgevet-mcp: install judgevet[mcp] to use this command",
            file=sys.stderr,
        )
        return 2

    selected = port is not None or provider_factory is not None
    stage = _Stage("provider acquisition" if selected else "credential resolution")
    try:
        if selected:
            configure_mcp_logging()
            asyncio.run(_run_selected(port, provider_factory, model, stage, texts))
            return 0
        return _run_hosted(model, stage, texts)
    except KeyboardInterrupt:
        return 130
    except (
        JudgevetError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        ExceptionGroup,
    ) as exc:
        raise SystemExit(_diagnostic(stage.name, (stage.error, exc))) from None


class _Stage:
    """Record the stage a fatal diagnostic names.

    Attributes:
        name (str): Stage in progress: audit sink, credential resolution,
            provider acquisition, serving or shutdown.
        error (Exception | None): Serving failure captured before cleanup
            runs, so a cleanup failure cannot replace it in the diagnostic.

    Examples:
        ```python
        from judgevet.adapters.inbound.mcp_entrypoint import _Stage

        assert _Stage("serving").name == "serving"
        ```
    """

    def __init__(self, name: str) -> None:
        """Start at the first stage of the selected path with no serving error.

        Args:
            name: Initial stage name.
        """
        self.name = name
        self.error: Exception | None = None


def _leaf_names(exc: BaseException) -> list[str]:
    """List distinct leaf exception type names in order of first appearance.

    Args:
        exc: Caught exception, possibly a nested group.

    Returns:
        Type names without module paths or exception text.
    """
    if not isinstance(exc, BaseExceptionGroup):
        return [type(exc).__name__]
    names = (name for inner in exc.exceptions for name in _leaf_names(inner))
    return list(dict.fromkeys(names))


def _diagnostic(stage: str, errors: Iterable[BaseException | None]) -> str:
    """Build the fixed fatal diagnostic from a stage and the exception types.

    Args:
        stage: Failed stage name.
        errors: Exceptions in reporting order; ``None`` entries are skipped.
            Only their type names are used, each distinct name once.

    Returns:
        The message ``judgevet-mcp: <stage> failed (<TypeName>, ...)``.
    """
    names = (name for exc in errors if exc is not None for name in _leaf_names(exc))
    return f"judgevet-mcp: {stage} failed ({', '.join(dict.fromkeys(names))})"


def _run_hosted(model: str, stage: _Stage, texts: dict[str, str] | None = None) -> int:
    """Preserve hosted settings and existing composition seams.

    Args:
        model: Explicit host-selected model. The default ``jev-latest``
            defers to ``settings.api.default_model``.
        stage: Stage record set to audit sink while the opted-in sink
            opens, then credential resolution, serving after it and shutdown
            after serving returns. It records a serving failure before the
            adapter closes. The sink closes after the adapter.
        texts: Launcher ``instructions`` and ``instructions_addendum``
            keyword options, or None for neither.

    Returns:
        Zero on success or two on configuration failure.

    Raises:
        Exception: The audit sink failed to open, serving failed, or a close
            failed.
    """
    try:
        settings = Settings()
    except ValidationError:
        print("judgevet-mcp: invalid settings", file=sys.stderr)
        return 2
    configure(settings.log)
    configure_mcp_logging()
    if not settings.api.has_key_source:
        print(
            "judgevet-mcp: set JEV_API__KEY or TYPESAFE_API_KEY, or JEV_API__KEY_FILE",
            file=sys.stderr,
        )
        return 2
    stage.name = "audit sink"
    path = settings.api.audit_path
    with nullcontext() if path is None else JsonlAuditSink(path) as sink:
        stage.name = "credential resolution"
        adapter = (
            build_adapter(settings)
            if sink is None
            else build_adapter(settings, audit=sink)
        )
        stage.name = "serving"
        chosen = settings.api.default_model if model == "jev-latest" else model
        options = {} if chosen == "jev-latest" else {"model": chosen}
        try:
            asyncio.run(run_stdio(adapter, **(texts or {}), **options))
            stage.name = "shutdown"
        except Exception as exc:
            stage.error = exc
            raise
        finally:
            adapter.close()
    return 0


async def _run_selected(
    port: SystemOnePort | None,
    factory: ProviderFactory | None,
    model: str,
    stage: _Stage,
    texts: dict[str, str] | None = None,
) -> None:
    """Serve an explicit provider inside its worker-owned context.

    Args:
        port: Borrowed provider.
        factory: Owning application factory.
        model: Host-selected model.
        stage: Stage record advanced to serving after provider acquisition
            and to shutdown after serving returns. It records a serving
            failure before the provider context exits.
        texts: Launcher ``instructions`` and ``instructions_addendum``
            keyword options, or None for neither.

    Raises:
        RuntimeError: Provider acquisition yielded no port.
        Exception: Serving failed, or the provider context's exit failed.
    """
    dispatch = ProviderDispatch(port=port, factory=factory)
    async with dispatch.session():
        if dispatch.port is None:
            raise RuntimeError("Provider acquisition did not return a port")
        stage.name = "serving"
        try:
            await run_stdio(dispatch.port, **(texts or {}), model=model)
        except Exception as exc:
            stage.error = exc
            raise
        stage.name = "shutdown"
