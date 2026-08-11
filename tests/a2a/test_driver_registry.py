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

    def test_register_remote(self, registry):
        from src.a2a.card_resolver import AgentCard, AgentSkill
        from src.a2a.http_driver import A2ADriver

        card = AgentCard(
            name="remote-gpt",
            description="Remote GPT agent",
            url="http://remote.local/v1",
            skills=[AgentSkill(id="chat", name="Chat", description="Chat completion")],
            version="1.0",
        )
        registry.register_remote(card)

        driver = registry.get("remote-gpt")
        assert driver is not None
        assert isinstance(driver, A2ADriver)
        assert driver.config.name == "remote-gpt"
        assert driver.base_url == "http://remote.local/v1"

    def test_register_remote_overwrites_existing(self, registry):
        from src.a2a.card_resolver import AgentCard, AgentSkill

        card1 = AgentCard(
            name="claude", description="", url="http://old/v1",
            skills=[], version="1.0",
        )
        card2 = AgentCard(
            name="claude", description="", url="http://new/v1",
            skills=[], version="2.0",
        )
        registry.register_remote(card1)
        registry.register_remote(card2)
        assert registry.get("claude").base_url == "http://new/v1"
