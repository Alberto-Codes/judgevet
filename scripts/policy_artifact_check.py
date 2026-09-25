"""Check supported policy imports and the base installation inside a wheel venv."""

import importlib
import importlib.util
import sysconfig
from pathlib import Path

import judgevet

_EXPORTS = {
    "judgevet.adapters.outbound.http": (
        "HTTPSystemOneAdapter",
        "AsyncHTTPSystemOneAdapter",
    ),
    "judgevet.adapters.outbound.gateway": ("GatewayConfig", "RequestMetadata"),
    "judgevet.adapters.outbound.network": ("NetworkConfig",),
    "judgevet.adapters.outbound.retries": ("RetryPolicy",),
    "judgevet.adapters.outbound.spend": ("SpendCap",),
    "judgevet.diagnostics": ("bind_request_id",),
    "judgevet.ports": ("SystemOnePort", "AsyncSystemOnePort", "StateRedactor"),
    "judgevet.domain.questions": ("Question", "Noul", "Choice", "Score"),
    "judgevet.domain.answers": ("Answer", "NoulAnswer", "ChoiceAnswer", "ScoreAnswer"),
    "judgevet.domain.response": ("SystemOneResponse",),
    "judgevet.domain.usage": ("Usage",),
    "judgevet.domain.errors": (
        "JevError",
        "JevAuthError",
        "JevBudgetExceededError",
        "JevRequestError",
        "JevMaxTokensExceededError",
        "JevResponseError",
        "JevServiceError",
        "JevRateLimitError",
    ),
}
_POLICY = {
    "ChoiceRule",
    "NoulRule",
    "ScoreRule",
    "Rule",
    "Policy",
    "ValidatedPolicy",
    "RuleReport",
    "PolicyReport",
    "PolicyError",
    "PolicyDefinitionError",
    "PolicyAnswerError",
    "validate_policy",
    "evaluate_policy",
}


def check_surface() -> None:
    """Require every supported name and original root export identity.

    Raises:
        RuntimeError: If any supported export is missing or changed.
    """
    names = {name for group in _EXPORTS.values() for name in group} | {
        "VERIFIED_MODEL",
        "__version__",
    }
    if set(judgevet.__all__) != names:
        raise RuntimeError("root __all__ differs from supported surface")
    for path, group in _EXPORTS.items():
        module = importlib.import_module(path)
        for name in group:
            if getattr(judgevet, name, None) is not getattr(module, name):
                raise RuntimeError(f"root export identity mismatch: {name}")
    for path, expected in (
        ("judgevet.policy", _POLICY),
        ("judgevet.policy_json", {"parse_policy"}),
    ):
        module = importlib.import_module(path)
        if set(module.__all__) != expected or any(
            not hasattr(module, name) for name in expected
        ):
            raise RuntimeError(f"supported facade mismatch: {path}")


def main() -> None:
    """Verify supported imports, installed location, typing marker and optionality.

    Raises:
        RuntimeError: If the base artifact fails an installation contract.
    """
    check_surface()
    location = Path(judgevet.__file__).resolve()
    if not location.is_relative_to(Path(sysconfig.get_paths()["purelib"]).resolve()):
        raise RuntimeError("judgevet is not imported from this environment's install")
    if not location.with_name("py.typed").is_file():
        raise RuntimeError("installed py.typed marker is missing")
    if importlib.util.find_spec("mcp") is not None:
        raise RuntimeError("base installation unexpectedly contains MCP")
    print(f"Policy artifact imports/base/typing marker passed: {location}")


if __name__ == "__main__":
    main()
