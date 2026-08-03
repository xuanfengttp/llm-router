# tests/gui/test_config_page.py
from __future__ import annotations

import pytest

from src.config.models import ModelConfig, ModelDeployment, ProviderConfig, ProviderStatus


class TestConfigPageData:
    """测试配置页的数据变换函数."""

    def test_provider_to_row(self):
        """Provider 转表格行."""
        from src.gui.pages.config_page import provider_to_row

        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-xxx",
            status=ProviderStatus.ONLINE,
            models=[
                ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD),
                ModelConfig(name="gpt-4o-mini", deployment=ModelDeployment.CLOUD),
            ],
        )
        row = provider_to_row(provider)
        assert row["name"] == "openai"
        assert row["endpoint"] == "https://api.openai.com/v1"
        assert row["model_count"] == 2
        assert row["status"] == "online"

    def test_provider_to_row_no_models(self):
        """无模型时 model_count 为 0."""
        from src.gui.pages.config_page import provider_to_row

        provider = ProviderConfig(name="empty", endpoint="http://x", status=ProviderStatus.UNKNOWN)
        row = provider_to_row(provider)
        assert row["model_count"] == 0
        assert row["status"] == "unknown"

    def test_model_to_row(self):
        """Model 转表格行."""
        from src.gui.pages.config_page import model_to_row

        model = ModelConfig(
            name="gpt-4o",
            deployment=ModelDeployment.CLOUD,
            cost_input_1k=2.5,
            cost_output_1k=10.0,
            context_window=128000,
        )
        row = model_to_row(model)
        assert row["name"] == "gpt-4o"
        assert row["cost_input"] == 2.5
        assert row["cost_output"] == 10.0
        assert row["context_window"] == 128000

    def test_connectivity_status_label(self):
        """延迟转状态标签."""
        from src.gui.pages.config_page import connectivity_label

        assert connectivity_label(None) == ("未测试", "grey")
        assert connectivity_label(150.0) == ("良好 (150ms)", "green")
        assert connectivity_label(800.0) == ("一般 (800ms)", "orange")
        assert connectivity_label(3500.0) == ("较差 (3500ms)", "red")
