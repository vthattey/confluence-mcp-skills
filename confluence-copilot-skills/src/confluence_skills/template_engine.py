"""Template loading, variable substitution, and serialisation."""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, Undefined


@dataclass
class Template:
    """A Confluence page template with metadata and a Jinja2-rendered body."""

    name: str
    description: str
    variables: list[dict[str, str]]       # [{name, description, required, default}]
    body: str                              # Confluence storage-format HTML with {{ placeholders }}
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_page_id: str | None = None      # set when template was extracted from a live page

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, values: dict[str, str]) -> str:
        """
        Substitute Jinja2 placeholders in the template body.

        Raises jinja2.UndefinedError if a required variable is missing.
        """
        env = Environment(undefined=StrictUndefined, autoescape=False)  # noqa: S701
        # pre-fill defaults for optional variables not supplied by caller
        context = {v["name"]: v.get("default", "") for v in self.variables}
        context.update(values)
        return env.from_string(self.body).render(context)

    def missing_required(self, values: dict[str, str]) -> list[str]:
        """Return names of required variables absent from values."""
        return [
            v["name"]
            for v in self.variables
            if v.get("required", True) and v["name"] not in values
        ]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "body": self.body,
            "created_at": self.created_at,
            "source_page_id": self.source_page_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Template":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            variables=data.get("variables", []),
            body=data["body"],
            created_at=data.get("created_at", ""),
            source_page_id=data.get("source_page_id"),
        )

    def save(self, directory: str) -> str:
        """Persist template as a JSON file. Returns the saved file path."""
        os.makedirs(directory, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]", "_", self.name.lower())
        path = os.path.join(directory, f"{safe_name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path: str) -> "Template":
        """Load a template from a JSON file."""
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


# ------------------------------------------------------------------
# Template registry
# ------------------------------------------------------------------

class TemplateRegistry:
    """Scans a directory and provides access to all saved templates."""

    def __init__(self, directory: str) -> None:
        self.directory = directory

    def list(self) -> list[str]:
        """Return template names (file stem, no extension) in the directory."""
        return [
            Path(f).stem
            for f in os.listdir(self.directory)
            if f.endswith(".json")
        ]

    def get(self, name: str) -> Template:
        """Load a template by name. Raises FileNotFoundError if absent."""
        safe_name = re.sub(r"[^\w\-]", "_", name.lower())
        path = os.path.join(self.directory, f"{safe_name}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template '{name}' not found in {self.directory}")
        return Template.load(path)

    def save(self, template: Template) -> str:
        """Save a template to the registry directory."""
        return template.save(self.directory)
