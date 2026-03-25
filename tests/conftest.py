import json
import pytest
from unittest.mock import MagicMock

from core.config_service import ConfigService
from core.events import EventBus
from core.provider import WorkbenchClient
from core.prompts import PromptRegistry
from core.storage import StorageManager
from ui.workspace_controller import WorkspaceController
from ui.app import App


@pytest.fixture
def temp_project_root(tmp_path):
    # Setup standard MVP project skeleton
    (tmp_path / "config" / "prompts").mkdir(parents=True)
    (tmp_path / "config" / "prompts" / "S1_v1.txt").write_text(
        "prompt context", encoding="utf-8"
    )
    (tmp_path / "config" / "prompts" / "analyze_v1.txt").write_text(
        "analyze context", encoding="utf-8"
    )
    (tmp_path / "config" / "prompts" / "S2_v1.txt").write_text(
        "prompt context 2", encoding="utf-8"
    )
    (tmp_path / "config" / "models.json").write_text(
        json.dumps(
            [{"id": "test-model-1", "name": "Basic Model", "capabilities": ["chat"]}]
        )
    )
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "runs").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def config_service(temp_project_root):
    return ConfigService(temp_project_root / "config")


@pytest.fixture
def storage(temp_project_root):
    return StorageManager(temp_project_root / "runs")


@pytest.fixture
def prompt_registry(temp_project_root):
    return PromptRegistry(temp_project_root / "config" / "prompts")


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=WorkbenchClient)
    client.base_url = "http://localhost"
    client.subscription_key = "test_key"
    return client


@pytest.fixture
def controller(
    temp_project_root, config_service, storage, prompt_registry, mock_client, event_bus
):
    ctrl = WorkspaceController(
        project_root=temp_project_root,
        config_service=config_service,
        storage=storage,
        prompt_registry=prompt_registry,
        client=mock_client,
        event_bus=event_bus,
    )
    # Automatically assume provider is ready since mock client is valid
    ctrl.state.is_provider_ready = True
    return ctrl


@pytest.fixture
def app(temp_project_root):
    # Create the app (will init services itself)
    app_instance = App(temp_project_root)
    yield app_instance
    app_instance.root.destroy()
