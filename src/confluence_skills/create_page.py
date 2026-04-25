"""Skill: create a Confluence page from a named template."""

import os
from typing import Any

from .client import ConfluenceClient
from .template_engine import Template, TemplateRegistry


def create_page_from_template(
    template_name: str,
    title: str,
    space_key: str,
    variables: dict[str, str],
    parent_id: str | None = None,
    template_dir: str | None = None,
) -> dict[str, Any]:
    """
    Create a new Confluence page by rendering a stored template.

    Parameters
    ----------
    template_name : str
        Name of the template file (without .json extension) in TEMPLATE_DIR.
    title : str
        Title of the page to create.
    space_key : str
        Confluence space key (e.g. 'ENG').
    variables : dict[str, str]
        Placeholder values to substitute into the template body.
    parent_id : str | None
        Optional parent page ID for nesting under an existing page.
    template_dir : str | None
        Override the default template directory.

    Returns
    -------
    dict
        {
          "page_id": str,
          "title": str,
          "url": str,
          "template_used": str,
          "space_key": str,
        }
    """
    directory = template_dir or os.environ.get("TEMPLATE_DIR", "templates")
    registry = TemplateRegistry(directory)
    template = registry.get(template_name)

    missing = template.missing_required(variables)
    if missing:
        raise ValueError(
            f"Template '{template_name}' requires these variables: {missing}"
        )

    rendered_body = template.render(variables)

    client = ConfluenceClient()
    space_id = client.get_space_id(space_key)
    page = client.create_page(
        space_id=space_id,
        title=title,
        body=rendered_body,
        parent_id=parent_id,
    )

    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
    return {
        "page_id": page["id"],
        "title": page["title"],
        "url": f"{base_url}/wiki/spaces/{space_key}/pages/{page['id']}",
        "template_used": template_name,
        "space_key": space_key,
    }


def list_templates(template_dir: str | None = None) -> list[str]:
    """Return names of all available templates."""
    directory = template_dir or os.environ.get("TEMPLATE_DIR", "templates")
    return TemplateRegistry(directory).list()


def describe_template(
    template_name: str, template_dir: str | None = None
) -> dict[str, Any]:
    """Return template metadata and its required variables."""
    directory = template_dir or os.environ.get("TEMPLATE_DIR", "templates")
    template = TemplateRegistry(directory).get(template_name)
    return {
        "name": template.name,
        "description": template.description,
        "variables": template.variables,
        "source_page_id": template.source_page_id,
        "created_at": template.created_at,
    }
