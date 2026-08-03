from __future__ import annotations

import pytest

from src.a2a.cli_driver import CLIDriver, DriverConfig
from src.a2a.driver_registry import DriverRegistry


class TestDriverRegistry:
    @pytest.fixture
    def driver(self):
        return CLIDriver(DriverConfig(name="claude", command="claude-internal"))

    @pytest.fixture
    def registry(self, driver):
        reg = DriverRegistry()
        reg.register(driver)
        return reg

    def test_register_and_get(self, registry, driver):
        assert registry.get("claude") is driver

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_list_all(self, registry):
        names = registry.list_all()
        assert "claude" in names

    def test_remove_existing(self, registry):
        registry.remove("claude")
        assert registry.get("claude") is None

    def test_remove_nonexistent(self, registry):
        with pytest.raises(KeyError):
            registry.remove("nope")

    def test_register_duplicate_succeeds(self, registry):
        new_driver = CLIDriver(DriverConfig(name="claude", command="other"))
        registry.register(new_driver)
        assert registry.get("claude") is new_driver
