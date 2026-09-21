"""Unit tests for ports."""

import pytest

from judgevet.ports import SystemOnePort


class TestSystemOnePort:
    """Tests for SystemOnePort."""

    def test_system_one_raises_not_implemented(self) -> None:
        """Test that calling system_one raises NotImplementedError."""
        port = SystemOnePort()
        with pytest.raises(NotImplementedError):
            port.system_one(state="test", questions={}, model="test")
