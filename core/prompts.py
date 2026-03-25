"""
core.prompts — Prompt registry and renderer.

Discovers prompt templates from config/prompts/ and renders them
with variable substitution.  Templates use a simple custom format:

    [system]
    You are a helpful assistant for $project_name.

    [user]
    Analyze the following: $input

Variable substitution uses Python string.Template ($variable).
"""

from __future__ import annotations

import re
from pathlib import Path
from string import Template
from typing import Optional


# Default prompts directory relative to project root
_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "config" / "prompts"

# Pattern for template filenames: {step_name}_v{version}.txt
_FILENAME_PATTERN = re.compile(r"^(.+)_v(\d+)\.txt$")

# Role markers inside template files
_ROLE_MARKER = re.compile(r"^\[(system|user|assistant)\]\s*$", re.IGNORECASE)


class PromptRegistry:
    """Discovers and renders prompt templates."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else _DEFAULT_PROMPTS_DIR

    def list_steps(self) -> list[str]:
        """Return distinct step names that have at least one template."""
        steps = set()
        if not self.prompts_dir.is_dir():
            return []
        for f in self.prompts_dir.iterdir():
            m = _FILENAME_PATTERN.match(f.name)
            if m:
                steps.add(m.group(1))
        return sorted(steps)

    def list_versions(self, step_name: str) -> list[str]:
        """Return available version strings for a given step name."""
        versions: list[str] = []
        if not self.prompts_dir.is_dir():
            return versions
        for f in self.prompts_dir.iterdir():
            m = _FILENAME_PATTERN.match(f.name)
            if m and m.group(1) == step_name:
                versions.append(m.group(2))
        return sorted(versions, key=int)

    def get_template_path(self, step_name: str, version: str) -> Path:
        """Return the path to a specific template file."""
        return self.prompts_dir / f"{step_name}_v{version}.txt"

    def render(
        self,
        step_name: str,
        version: str,
        variables: dict[str, str],
    ) -> list[dict[str, str]]:
        """
        Render a prompt template into a list of chat messages.

        Returns a list of dicts: [{"role": "system", "content": "..."}, ...]

        Raises FileNotFoundError if the template does not exist.
        """
        path = self.get_template_path(step_name, version)
        if not path.is_file():
            raise FileNotFoundError(
                f"Prompt template not found: {path.name} (looked in {self.prompts_dir})"
            )

        raw = path.read_text(encoding="utf-8")
        return self._parse_and_render(raw, variables)

    def render_preview(
        self,
        raw_text: str,
        variables: dict[str, str],
    ) -> list[dict[str, str]]:
        """
        Render a raw prompt template string (for example, from an in-memory
        draft) into a list of chat messages.
        Use this for previewing templates in the UI before saving.
        """
        return self._parse_and_render(raw_text, variables)

    def _parse_and_render(
        self,
        raw_text: str,
        variables: dict[str, str],
    ) -> list[dict[str, str]]:
        """Parse role markers, substitute variables, return messages."""
        messages: list[dict[str, str]] = []
        current_role: Optional[str] = None
        current_lines: list[str] = []

        for line in raw_text.splitlines():
            marker = _ROLE_MARKER.match(line.strip())
            if marker:
                # Flush previous block
                if current_role is not None:
                    content = self._substitute(
                        "\n".join(current_lines).strip(), variables
                    )
                    messages.append({"role": current_role, "content": content})
                current_role = marker.group(1).lower()
                current_lines = []
            else:
                current_lines.append(line)

        # Flush last block
        if current_role is not None:
            content = self._substitute("\n".join(current_lines).strip(), variables)
            messages.append({"role": current_role, "content": content})

        # If no role markers found, treat entire text as a user message
        if not messages:
            content = self._substitute(raw_text.strip(), variables)
            messages.append({"role": "user", "content": content})

        return messages

    def render_from_parts(
        self,
        role_text: str,
        task_text: str,
        upstream_output: str = "",
        extra_variables: Optional[dict] = None,
    ) -> list[dict[str, str]]:
        """Render prompt from no-code role + task fields.

        Automatically prepends upstream_output (previous step result) to the
        user message so users never need to type $input.

        Parameters
        ----------
        role_text : str
            System-level instruction ("You are a helpful business analyst…")
        task_text : str
            User-level task ("Analyze the following document…")
        upstream_output : str
            Output from the previous step or initial user context.
        extra_variables : dict
            Additional variables for substitution (e.g., attachment contents).

        Returns
        -------
        list of {role, content} dicts.
        """
        variables = dict(extra_variables or {})
        variables["input"] = upstream_output

        messages: list[dict[str, str]] = []

        if role_text.strip():
            messages.append(
                {
                    "role": "system",
                    "content": self._substitute(role_text.strip(), variables),
                }
            )

        # Build user content: task + upstream context appended below
        user_parts = []
        if task_text.strip():
            user_parts.append(self._substitute(task_text.strip(), variables))
        if upstream_output.strip():
            user_parts.append(f"\n\n---\n{upstream_output.strip()}")
        user_content = "".join(user_parts)

        if user_content:
            messages.append({"role": "user", "content": user_content})
        elif not messages:
            # Fallback: at least one message
            messages.append(
                {"role": "user", "content": upstream_output.strip() or "(no input)"}
            )

        return messages

    @staticmethod
    def _substitute(text: str, variables: dict[str, str]) -> str:
        """Safe variable substitution using string.Template."""
        try:
            return Template(text).safe_substitute(variables)
        except (ValueError, KeyError):
            return text
