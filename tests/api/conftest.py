import sys
from pathlib import Path

# Add both project root and backend/ to sys.path so that `src` becomes
# a namespace package spanning project_root/src/ and backend/src/.
_project_root = str(Path(__file__).parent.parent.parent.resolve())
_backend_dir = str(Path(_project_root) / "backend")
for d in (_project_root, _backend_dir):
    if d not in sys.path:
        sys.path.insert(0, d)

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.config.models import ProviderConfig, ModelConfig, ModelDeployment, ProviderStatus


@pytest.fixture
def mock_providers():
    """Return mutable provider list for tests to populate."""
    return []


@pytest.fixture
def mock_store(mock_providers):
    store = MagicMock()
    store.close = AsyncMock()
    store.init_db = AsyncMock()
    store.record_latency = AsyncMock()
    store.get_latency_history = AsyncMock(return_value=[])
    store.load_providers = MagicMock(return_value=mock_providers)
    store.save_providers = MagicMock()
    return store


@pytest.fixture
def mock_config_manager(mock_providers, mock_store):
    """Create a ConfigManager backed by mock store and mutable providers list."""
    from src.config.manager import ConfigManager
    mgr = ConfigManager(mock_store)
    mgr._providers = mock_providers
    mgr._store.load_providers = MagicMock(return_value=mock_providers)
    return mgr


@pytest.fixture
def client(mock_config_manager):
    from src.api.config_api import router
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.config_manager = mock_config_manager
    return TestClient(app)


@pytest.fixture
def mock_network_probe():
    from collections import namedtuple
    ProbeResult = namedtuple('ProbeResult', ['success', 'latency_ms', 'error'])

    class MockProbe:
        async def ping_chat_endpoint(self, provider, model, endpoint, api_key=None):
            if provider == 'nonexist':
                return ProbeResult(False, None, 'Unknown provider')
            return ProbeResult(True, 234.5, None)

    return MockProbe()


@pytest.fixture
def dashboard_client(mock_config_manager, mock_network_probe):
    from backend.src.api.dashboard_api import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.config_manager = mock_config_manager
    app.state.network_probe = mock_network_probe
    from fastapi.testclient import TestClient
    return TestClient(app)
