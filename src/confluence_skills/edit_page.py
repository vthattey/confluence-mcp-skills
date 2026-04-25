"""Skill: edit an existing Confluence page — full replace or section merge."""

import re
from typing import Any

from .client import ConfluenceClient
from .template_engine import Template, TemplateRegistry
import os


def edit_page(
    page_id: str,
    new_body: str | None = None,
    new_title: str | None = None,
    template_name: str | None = None,
    variables: dict[str, str] | None = None,
    template_dir: str | None = None,
) -> dict[str, Any]:
    """
    Replace the body (and optionally the title) of an existing Confluence page.

    Provide either `new_body` directly OR `template_name` + `variables`.
    If both are given, `new_body` takes precedence.

    Parameters
    ----------
    page_id : str
        The numeric ID of the page to update.
    new_body : str | None
        Raw Confluence storage-format HTML to write. Replaces the entire page body.
    new_title : str | None
        New title. If None, the existing title is kept.
    template_name : str | None
        Name of a saved template to render as the new body.
    variables : dict | None
        Template variable values (used when template_name is supplied).
    template_dir : str | None
        Override the default template directory.

    Returns
    -------
    dict
        {
          "page_id": str,
          "title": str,
          "version": int,
          "url": str,
        }
    """
    client = ConfluenceClient()
    current = client.get_page(page_id)
    current_version = current["version"]["number"]
    current_title = current["title"]

    if new_body is None:
        if template_name is None:
            raise ValueError("Provide either new_body or template_name.")
        directory = template_dir or os.environ.get("TEMPLATE_DIR", "templates")
        template = TemplateRegistry(directory).get(template_name)
        new_body = template.render(variables or {})

    updated = client.update_page(
        page_id=page_id,
        title=new_title or current_title,
        body=new_body,
        version=current_version + 1,
    )

    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
    space_key = updated.get("spaceKey", "")
    return {
        "page_id": updated["id"],
        "title": updated["title"],
        "version": updated["version"]["number"],
        "url": f"{base_url}/wiki/spaces/{space_key}/pages/{updated['id']}",
    }


def append_section(
    page_id: str,
    section_heading: str,
    section_body: str,
    heading_level: int = 2,
) -> dict[str, Any]:
    """
    Append a new section to the end of an existing page body.

    Parameters
    ----------
    page_id : str
        Target page ID.
    section_heading : str
        Heading text for the new section.
    section_body : str
        Confluence storage-format HTML content for the section.
    heading_level : int
        Heading level 1–6 (default 2).

    Returns
    -------
    dict  — same shape as edit_page()
    """
    client = ConfluenceClient()
    current = client.get_page(page_id, body_format="storage")
    existing_body = current.get("body", {}).get("storage", {}).get("value", "")

    heading_tag = f"h{heading_level}"
    new_section = (
        f"<{heading_tag}>{section_heading}</{heading_tag}>"
        f"{section_body}"
    )
    merged_body = existing_body + new_section

    return edit_page(page_id=page_id, new_body=merged_body)


def replace_section(
    page_id: str,
    section_heading: str,
    new_section_body: str,
    heading_level: int = 2,
) -> dict[str, Any]:
    """
    Replace the content of a named section within a page body.

    Finds the section by its heading text and replaces everything between that
    heading and the next same-level (or higher) heading.

    Returns
    -------
    dict  — same shape as edit_page()
    """
    client = ConfluenceClient()
    current = client.get_page(page_id, body_format="storage")
    existing_body = current.get("body", {}).get("storage", {}).get("value", "")

    level = heading_level
    # Match from the target heading up to (but not including) the next h{level} or above
    pattern = (
        rf"(<h{level}>{re.escape(section_heading)}</h{level}>)"
        rf"(.*?)"
        rf"(?=<h[1-{level}]|$)"
    )
    replacement = rf"\1{new_section_body}"
    updated_body, count = re.subn(pattern, replacement, existing_body, flags=re.DOTALL)

    if count == 0:
        raise ValueError(
            f"Section heading '{section_heading}' not found at h{level} in page {page_id}."
        )

    return edit_page(page_id=page_id, new_body=updated_body)
