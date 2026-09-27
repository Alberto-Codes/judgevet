"""Compose CLI calls with explicitly selected application providers.

Input parsing precedes provider acquisition. The application owns configuration,
state transformations, audit and spend accounting through its selected provider.
Image manifests are bounded and validated before entering the same resource scope.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_composition import ProviderSelection
    from judgevet.testing import FakeSystemOnePort

    provider = FakeSystemOnePort()
    selection = ProviderSelection(provider, None)
    assert selection.port is provider
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Public application factory.
    - [judgevet.providers][]: Explicit resource ownership.
    - [judgevet.adapters.inbound.cli_policy_run][]: Existing policy rendering.
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import typer

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_media import load_evidence
from judgevet.adapters.inbound.cli_options import FileInputs, file_values
from judgevet.adapters.inbound.cli_policy_run import (
    CliCallbacks,
    _load_policy,
    _render_policy,
)
from judgevet.domain.errors import JudgevetError
from judgevet.media import judge_with_images
from judgevet.ports import SystemOnePort
from judgevet.providers import ProviderFactory, provider_scope


@dataclass(frozen=True)
class ProviderSelection:
    """Retain one application's provider selection without acquiring it.

    Attributes:
        port (SystemOnePort | None): Borrowed provider, if supplied.
        factory (ProviderFactory | None): Owning context factory, if supplied.

    Examples:
        ```python
        from judgevet.adapters.inbound.cli_composition import ProviderSelection
        from judgevet.testing import FakeSystemOnePort

        selection = ProviderSelection(FakeSystemOnePort(), None)
        assert selection.factory is None
        ```
    """

    port: SystemOnePort | None
    factory: ProviderFactory | None


def run_selected(
    selection: ProviderSelection,
    state: str,
    questions: str,
    model: str,
    as_json: bool,
    files: FileInputs,
    callbacks: CliCallbacks,
) -> int:
    """Validate input, call the selected provider and render its typed response.

    Args:
        selection: Explicit borrowed port or owning factory.
        state: Existing state string interpretation.
        questions: Existing question JSON.
        model: Requested model identifier.
        as_json: Select machine output.
        files: Optional explicit policy and evidence paths.
        callbacks: Existing parsing and rendering boundaries.

    Returns:
        Zero for success, three for unmet policy, or one for handled failure.
    """
    try:
        typed_questions = callbacks.parse(questions)
        rules = (
            _load_policy(files.policy, typed_questions)
            if files.policy is not None
            else None
        )
        evidence = load_evidence(files.evidence, typed_questions)
        state_data = json.loads(state) if state.startswith(("{", "[")) else state
        with provider_scope(port=selection.port, factory=selection.factory) as port:
            response = (
                judge_with_images(
                    port, state_data, typed_questions, model, evidence=evidence
                )
                if evidence is not None
                else port.system_one(
                    state=state_data, questions=typed_questions, model=model
                )
            )
            if rules is not None:
                return _render_policy(
                    response, rules, as_json, callbacks.build, callbacks.output
                )
            callbacks.output(callbacks.build(response), as_json)
            return 0
    except (InputFailure, JudgevetError) as error:
        message = str(error)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        message = (
            "Invalid state, questions or configuration for policy judgment"
            if files.policy is not None
            else str(error)
        )
    print(
        json.dumps({"error": message}) if as_json else f"Error: {message}",
        file=sys.stderr,
    )
    return 1


CommandDispatch = Callable[[str, str, str, str | None, bool, FileInputs], int]
CommandInputs = Callable[
    [
        str | None,
        str | None,
        list[str] | None,
        list[str] | None,
        list[str] | None,
        bool,
    ],
    tuple[str, str],
]
MAX_POSITIONAL_INPUTS = 2


@dataclass(frozen=True)
class CliCommand:
    """Bind the shared command grammar to one application's dispatch.

    Attributes:
        dispatch (CommandDispatch): Selected composition root.
        inputs (CommandInputs): Existing explicit input validation.

    Examples:
        ```python
        from judgevet.adapters.inbound.cli_composition import CliCommand

        command = CliCommand(
            lambda state, questions, model, key, output, policies: 0,
            lambda state, questions, states, queries, policies, output: ("s", "{}"),
        )
        assert callable(command.run)
        ```
    """

    dispatch: CommandDispatch
    inputs: CommandInputs

    def run(
        self,
        ctx: typer.Context,
        arguments: Annotated[
            list[str] | None,
            typer.Argument(
                help=("state: State to evaluate. questions: Questions as JSON string."),
                metavar="[STATE] [QUESTIONS]",
            ),
        ] = None,
        model: str = typer.Option("jev-latest", help="Model to use"),
        api_key: str | None = typer.Option(None, help="TypeSafe API key"),
        json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> int:
        """Validate command inputs and dispatch to the selected composition root.

        Args:
            ctx: Invocation metadata and application provider selection.
            arguments: Optional positional state followed by questions JSON.
            model: Model to use.
            api_key: TypeSafe API key.
            json_output: Output as JSON.

        Returns:
            0 on success. Failures raise typer.Exit.

        Raises:
            typer.Exit: If input validation or the judgment fails.
            typer.BadParameter: If required legacy positional arguments are absent.
        """
        state_files = file_values(ctx, "state_file")
        question_files = file_values(ctx, "questions_file")
        policy_files = file_values(ctx, "policy")
        evidence_files = file_values(ctx, "evidence_file")
        if len(evidence_files) > 1:
            message = "--evidence-file: specify one evidence file"
            print(
                json.dumps({"error": message}) if json_output else f"Error: {message}",
                file=sys.stderr,
            )
            raise typer.Exit(1)
        positions = arguments or []
        if len(positions) > MAX_POSITIONAL_INPUTS:
            raise typer.BadParameter("Expected at most state and questions")
        state = positions[0] if positions else None
        questions = positions[1] if len(positions) == MAX_POSITIONAL_INPUTS else None
        state, questions = self.inputs(
            state, questions, state_files, question_files, policy_files, json_output
        )
        code = self.dispatch(
            state,
            questions,
            model,
            api_key,
            json_output,
            FileInputs(
                policy_files[0] if policy_files else None,
                evidence_files[0] if evidence_files else None,
            ),
        )
        if code != 0:
            raise typer.Exit(code=code)
        return code
