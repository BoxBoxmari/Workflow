"""
core.config_service — File-based configuration service.

Encapsulates reading, writing, and listing workflows and prompts.
UI editors should interact with this service rather than direct file paths.
"""

import json
import logging
from pathlib import Path


from core.io_utils import atomic_write_json
from core.migrations import migrate, normalize_workflow_dict
from core.models import WorkflowDef
from core.prompts import PromptRegistry

log = logging.getLogger("workbench.core.config_service")


class ConfigService:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.workflows_file = self.config_dir / "workflows.json"
        self.prompts_dir = self.config_dir / "prompts"

        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.registry = PromptRegistry(self.prompts_dir)

    # ---------------------------------------------------------
    # Models
    # ---------------------------------------------------------

    def load_models(self, capability_filter: str | None = "chat") -> list[str]:
        """Load model IDs from config/models.json, optionally filtered by capability.

        Parameters
        ----------
        capability_filter : str | None
            If set, only return models whose 'capabilities' list includes this
            string.  Models without a 'capabilities' field are always kept for
            backward compatibility (treated as chat-capable by default).
            Pass ``None`` to return every model in the file.
        """
        models_file = self.config_dir / "models.json"
        if not models_file.is_file():
            return ["gpt-4o-2024-08-06-gs-ae"]
        try:
            data = json.loads(models_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = data.get("models", [])

            result: list[str] = []
            for m in data:
                if isinstance(m, dict):
                    model_id = m.get("id") or m.get("name") or str(m)
                    caps = m.get("capabilities")
                    # Backward-compat: no capabilities field → assume chat
                    if (
                        capability_filter is None
                        or caps is None
                        or capability_filter in caps
                    ):
                        result.append(str(model_id))
                else:
                    result.append(str(m))
            return result
        except Exception:
            return ["gpt-4o-2024-08-06-gs-ae"]

    def is_valid_model(self, model_id: str) -> bool:
        """Check if a model ID exists in the catalog."""
        if not model_id:
            return False
        # capability_filter=None gets ALL models from the file
        supported = self.load_models(capability_filter=None)
        return model_id in supported

    # ---------------------------------------------------------
    # Workflows
    # ---------------------------------------------------------

    def load_workflows(self) -> list[WorkflowDef]:
        """Load all workflow definitions from config/workflows.json.

        Runs schema migration pipeline on load to upgrade legacy configs.
        """
        if not self.workflows_file.is_file():
            return []

        try:
            raw = json.loads(self.workflows_file.read_text(encoding="utf-8"))
            # Wrap bare list into dict so migration pipeline can work
            if isinstance(raw, list):
                raw = {"workflows": raw}
            migrated = migrate(raw)
            items = migrated.get("workflows", [])
            return [
                WorkflowDef.from_dict(normalize_workflow_dict(item)) for item in items
            ]
        except Exception as e:
            log.warning("Failed to load workflows: %s", e)
            return []

    def save_workflows(self, workflows: list[WorkflowDef]) -> None:
        """Save workflow definitions to config/workflows.json atomically."""
        workflow_items: list[dict] = []
        for wf in workflows:
            wf_dict = wf.to_dict()
            wf_dict["schema_version"] = 3
            workflow_items.append(wf_dict)
        data = {"schema_version": 3, "workflows": workflow_items}
        atomic_write_json(self.workflows_file, data)

    # ---------------------------------------------------------
    # Prompts
    # ---------------------------------------------------------

    def list_prompt_steps(self) -> list[str]:
        """Return available step names."""
        return self.registry.list_steps()

    def list_prompt_versions(self, step_name: str) -> list[str]:
        """Return numeric versions existing for a step name."""
        return self.registry.list_versions(step_name)

    def load_prompt(self, step_name: str, version: str) -> str:
        """Read prompt file contents."""
        path = self.registry.get_template_path(step_name, version)
        if not path.is_file():
            raise FileNotFoundError(f"Prompt {path.name} not found.")
        return path.read_text(encoding="utf-8")

    def save_prompt(self, step_name: str, version: str, content: str) -> Path:
        """Write prompt to file using atomic replacement."""
        if not version.isdigit():
            raise ValueError("Prompt version must be a numeric string.")

        path = self.registry.get_template_path(step_name, version)
        temp_file = path.with_suffix(".tmp")
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(path)
        return path

    def delete_prompt(self, step_name: str, version: str) -> None:
        """Remove a prompt file."""
        path = self.registry.get_template_path(step_name, version)
        if path.is_file():
            path.unlink()

    def next_prompt_version(self, step_name: str) -> str:
        """Find the next available version number for a step."""
        versions = self.list_prompt_versions(step_name)
        if not versions:
            return "1"
        return str(int(versions[-1]) + 1)
