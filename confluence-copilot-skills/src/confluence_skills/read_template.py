"""Skill: read a live Confluence page and extract a reusable template from it."""

import os
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .client import ConfluenceClient
from .template_engine import Template, TemplateRegistry

# ----------------------------------------------------------------------------
# Default extraction rules
# Text matching these patterns is replaced with Jinja2 placeholders.
# Rules are applied in order — first match wins per text node.
# ----------------------------------------------------------------------------
DEFAULT_EXTRACTION_RULES: list[dict[str, Any]] = [
    {
        "name": "title",
        "description": "Page title",
        "pattern": r".+",           # entire <title> element — handled separately
        "required": True,
        "default": "",
        "scope": "title",           # applied to page title, not body
    },
    {
        "name": "author",
        "description": "Author full name",
        "pattern": r"\bWritten by\b.+",
        "required": False,
        "default": "",
        "scope": "body",
    },
    {
        "name": "date",
        "description": "Document date (ISO-8601: YYYY-MM-DD)",
        "pattern": r"\d{4}-\d{2}-\d{2}",
        "required": False,
        "default": "",
        "scope": "body",
    },
    {
        "name": "version",
        "description": "Document version (e.g. 1.0.0)",
        "pattern": r"\bv?\d+\.\d+(?:\.\d+)?\b",
        "required": False,
        "default": "1.0.0",
        "scope": "body",
    },
]


def extract_template_from_page(
    page_id: str,
    template_name: str,
    template_description: str = "",
    extra_rules: list[dict[str, Any]] | None = None,
    template_dir: str | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """
    Read a Confluence page and convert it into a reusable template.

    The skill:
    1. Fetches the page body in Confluence storage format (HTML).
    2. Walks every text node and replaces content that matches the extraction
       rules with Jinja2 ``{{ variable_name }}`` placeholders.
    3. Preserves all HTML structure, macros, and formatting exactly.
    4. Saves the resulting Template to disk (unless save=False).

    Parameters
    ----------
    page_id : str
        ID of the source Confluence page.
    template_name : str
        Human-readable name for the saved template.
    template_description : str
        Optional description stored with the template.
    extra_rules : list | None
        Additional extraction rules appended to the defaults.
        Each rule dict: {name, description, pattern, required, default, scope}
    template_dir : str | None
        Directory to save the template JSON. Defaults to TEMPLATE_DIR env var.
    save : bool
        If True (default), save the template to disk and return the file path.

    Returns
    -------
    dict
        {
          "template_name": str,
          "saved_path": str | None,
          "variables": list[dict],
          "source_page_id": str,
          "source_page_title": str,
          "body_preview": str,           # first 500 chars of rendered template body
        }
    """
    client = ConfluenceClient()
    page = client.get_page(page_id, body_format="storage")

    source_title = page["title"]
    raw_body = page.get("body", {}).get("storage", {}).get("value", "")

    rules = DEFAULT_EXTRACTION_RULES + (extra_rules or [])

    # Apply title rule
    processed_title = "{{ title }}"

    # Apply body rules
    processed_body, detected_variables = _apply_rules_to_body(raw_body, rules)

    # Build variable definitions from rules that were actually detected
    detected_names = {v["name"] for v in detected_variables}
    variables = [
        {
            "name": r["name"],
            "description": r["description"],
            "required": r.get("required", True),
            "default": r.get("default", ""),
        }
        for r in rules
        if r["name"] in detected_names or r.get("required", False)
    ]

    template = Template(
        name=template_name,
        description=template_description or f"Template extracted from page {source_title}",
        variables=variables,
        body=processed_body,
        source_page_id=page_id,
    )

    saved_path: str | None = None
    if save:
        directory = template_dir or os.environ.get("TEMPLATE_DIR", "templates")
        saved_path = TemplateRegistry(directory).save(template)

    return {
        "template_name": template_name,
        "saved_path": saved_path,
        "variables": variables,
        "source_page_id": page_id,
        "source_page_title": source_title,
        "body_preview": processed_body[:500],
    }


def preview_template_extraction(page_id: str) -> dict[str, Any]:
    """
    Dry-run extraction — return what would be detected without saving anything.

    Useful for previewing which text fragments will become placeholders before
    committing to saving the template.
    """
    return extract_template_from_page(
        page_id=page_id,
        template_name="_preview",
        save=False,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_rules_to_body(
    html_body: str,
    rules: list[dict[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    """
    Walk all text nodes in the HTML body and apply extraction rules.

    Returns the modified HTML string and a list of detected variable names.
    """
    soup = BeautifulSoup(html_body, "lxml-xml")
    detected: list[dict[str, str]] = []
    detected_names: set[str] = set()

    body_rules = [r for r in rules if r.get("scope", "body") == "body"]

    for text_node in soup.find_all(string=True):
        if not isinstance(text_node, str):
            continue
        # Skip text inside macro metadata tags
        if _is_inside_macro_param(text_node):
            continue

        new_text = text_node
        for rule in body_rules:
            pattern = rule["pattern"]
            placeholder = f"{{{{ {rule['name']} }}}}"
            new_text, was_replaced = _replace_pattern(new_text, pattern, placeholder)
            if was_replaced and rule["name"] not in detected_names:
                detected_names.add(rule["name"])
                detected.append({"name": rule["name"]})

        if new_text != text_node:
            text_node.replace_with(new_text)

    return str(soup), detected


def _replace_pattern(text: str, pattern: str, replacement: str) -> tuple[str, bool]:
    """Replace first match of pattern with replacement. Returns (new_text, was_replaced)."""
    new_text, count = re.subn(pattern, replacement, text, count=1)
    return new_text, count > 0


def _is_inside_macro_param(tag: Any) -> bool:
    """Return True if the tag is nested inside a Confluence macro parameter element."""
    parent = getattr(tag, "parent", None)
    while parent:
        if isinstance(parent, Tag) and parent.name in (
            "ac:parameter",
            "ac:plain-text-body",
            "ac:rich-text-body",
        ):
            return True
        parent = getattr(parent, "parent", None)
    return False
