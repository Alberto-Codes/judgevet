"""Supported JSON decoding facade for typed policies.

The grammar matches CLI policy files. Errors are local PolicyDefinitionError
instances without CLI prefixes or exit codes. Callers own file and stdin IO.

Examples:
    ```python
    from judgevet import Noul, NoulAnswer
    from judgevet.policy import evaluate_policy
    from judgevet.policy_json import parse_policy

    policy = parse_policy(
        '{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}',
        {"clear": Noul(instructions="Clear?")},
    )
    assert evaluate_policy(policy, {"clear": NoulAnswer(0.9)}).passed
    ```

See Also:
    - [judgevet.policy][]: Pure typed construction and evaluation.
    - [judgevet.adapters.inbound.cli_policy][]: Legacy CLI error translation.
"""

from judgevet._policy_json import parse_policy

__all__ = ["parse_policy"]
