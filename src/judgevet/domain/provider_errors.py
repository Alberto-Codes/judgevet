"""Neutral errors for application-owned judgment providers.

Applications map known backend failures to these classes using safe messages.
Unexpected exceptions retain their original types. These errors add no HTTP
status or retry guarantees.
Source: https://github.com/Alberto-Codes/judgevet/issues/200#issuecomment-5850335591.

Examples:
    ```python
    from judgevet.domain.provider_errors import ProviderUnavailableError

    error = ProviderUnavailableError("Install the application provider extra")
    assert str(error) == "Install the application provider extra"
    ```

See Also:
    - [judgevet.domain.errors][]: Neutral library error base.
    - [judgevet.providers][]: Provider selection and lifetime ownership.
"""

from judgevet.domain.errors import JudgevetError


class ProviderError(JudgevetError):
    """Base for declared application provider failures.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderError

        error = ProviderError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """


class ProviderUnavailableError(ProviderError):
    """The selected provider cannot be acquired or used.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderUnavailableError

        error = ProviderUnavailableError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """


class ProviderRequestError(ProviderError):
    """The provider rejects the supplied request.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderRequestError

        error = ProviderRequestError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """


class ProviderCapabilityError(ProviderError):
    """The selected provider does not support a required capability.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderCapabilityError

        error = ProviderCapabilityError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """


class ProviderTransportError(ProviderError):
    """Communication with the selected provider failed.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderTransportError

        error = ProviderTransportError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """


class ProviderResponseError(ProviderError):
    """The provider returned data that violates the typed answer contract.

    Attributes:
        args (tuple): Standard exception arguments containing a safe message.

    Examples:
        ```python
        from judgevet.providers import ProviderResponseError

        error = ProviderResponseError("Synthetic provider failure")
        assert str(error) == "Synthetic provider failure"
        ```
    """
