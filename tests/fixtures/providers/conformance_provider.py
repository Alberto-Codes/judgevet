"""A provider test module the runner executes against the installed kit (#241).

A provider package writes a module like this one in its own test suite. It
subclasses the kit's base class and overrides the fixtures that supply its
implementation. The installed-artifact runner runs it with pytest inside the
``conformance`` environment and requires every rule test to pass.
"""

from contextlib import nullcontext

import pytest

from judgevet.providers import ProviderFactory
from judgevet.testing import FakeSystemOnePort
from judgevet.testing.conformance import VALID_ANSWERS, BaseProviderConformance
from tests.fixtures.providers.provider_fixture import RecordingProvider


class TestInstalledProvider(BaseProviderConformance):
    """The public fake and the application fixture pass every rule."""

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Borrow a scripted fake per scope.

        Returns:
            A factory whose context yields a fake with the kit's answers.
        """
        return lambda: nullcontext(FakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self) -> RecordingProvider:
        """Raise a transport failure from every judgment.

        Returns:
            A recording provider configured to fail.
        """
        return RecordingProvider("installed-failing", fail=True)

    @pytest.fixture
    def media_port(self) -> RecordingProvider:
        """Declare PNG and JPEG support only.

        Returns:
            A recording provider with media support.
        """
        return RecordingProvider("installed-media")
