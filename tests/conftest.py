# tests/conftest.py
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def example_providers():
    """示例 Provider 配置数据。"""
    return [
        {
            "name": "openai",
            "endpoint": "https://api.openai.com/v1",
            "api_key": "sk-test-openai-key-12345",
            "models": [
                {
                    "name": "gpt-4o",
                    "deployment": "cloud",
                    "context_window": 128000,
                    "cost_input_1k": 0.0025,
                    "cost_output_1k": 0.0100,
                    "tags": ["smart", "cloud", "expensive"],
                },
                {
                    "name": "gpt-4o-mini",
                    "deployment": "cloud",
                    "context_window": 128000,
                    "cost_input_1k": 0.00015,
                    "cost_output_1k": 0.0006,
                    "tags": ["cheap", "cloud", "fast"],
                },
            ],
        },
        {
            "name": "anthropic",
            "endpoint": "https://api.anthropic.com/v1",
            "api_key": "sk-ant-test-key-67890",
            "models": [
                {
                    "name": "claude-opus-5",
                    "deployment": "cloud",
                    "context_window": 200000,
                    "cost_input_1k": 0.015,
                    "cost_output_1k": 0.075,
                    "tags": ["smart", "cloud", "expensive"],
                },
            ],
        },
        {
            "name": "ollama-local",
            "endpoint": "http://localhost:11434",
            "api_key": None,
            "models": [
                {
                    "name": "qwen2.5:7b",
                    "deployment": "local",
                    "context_window": 32768,
                    "cost_input_1k": 0.0,
                    "cost_output_1k": 0.0,
                    "tags": ["cheap", "local", "basic"],
                },
            ],
        },
    ]
