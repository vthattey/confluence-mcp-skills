"""
MCP server — exposes all Confluence skills as tools for GitHub Copilot.

Run:
    python mcp_server.py

GitHub Copilot (and any MCP client) will discover all tools via the
Model Context Protocol stdio transport.
"""

import json
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.confluence_skills.add_attachment import (
    add_attachment,
    add_multiple_attachments,
    list_attachments,
)
from src.confluence_skills.create_page import (
    create_page_from_template,
    describe_template,
    list_templates,
)
from src.confluence_skills.edit_page import (
    append_section,
    edit_page,
    replace_section,
)
from src.confluence_skills.read_template import (
    extract_template_from_page,
    preview_template_extraction,
)

app = Server("confluence-copilot-skills")


# ---------------------------------------------------------------------------
# Tool: confluence_create_page
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_create_page(
    template_name: str,
    title: str,
    space_key: str,
    variables: dict,
    parent_id: str = "",
) -> list[TextContent]:
    """
    Create a new Confluence page by rendering a stored template.

    Parameters
    ----------
    template_name : str
        Name of the template to use (from TEMPLATE_DIR).
    title : str
        Title of the new page.
    space_key : str
        Confluence space key (e.g. 'ENG').
    variables : dict
        Key-value pairs for template placeholder substitution.
    parent_id : str
        Optional parent page ID for page nesting. Leave empty for root.
    """
    result = create_page_from_template(
        template_name=template_name,
        title=title,
        space_key=space_key,
        variables=variables,
        parent_id=parent_id or None,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_list_templates
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_list_templates() -> list[TextContent]:
    """List all available Confluence page templates stored in TEMPLATE_DIR."""
    names = list_templates()
    return [TextContent(type="text", text=json.dumps({"templates": names}, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_describe_template
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_describe_template(template_name: str) -> list[TextContent]:
    """
    Return metadata and required variables for a named template.

    Parameters
    ----------
    template_name : str
        Name of the template to inspect.
    """
    info = describe_template(template_name)
    return [TextContent(type="text", text=json.dumps(info, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_edit_page
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_edit_page(
    page_id: str,
    new_body: str = "",
    new_title: str = "",
    template_name: str = "",
    variables: dict | None = None,
) -> list[TextContent]:
    """
    Replace the body (and optionally the title) of an existing Confluence page.

    Provide either new_body directly, or template_name + variables.

    Parameters
    ----------
    page_id : str
        Numeric ID of the page to update.
    new_body : str
        Raw Confluence storage-format HTML. Replaces the entire page body.
    new_title : str
        New page title. Leave empty to keep the current title.
    template_name : str
        Name of a saved template to render as the new body.
    variables : dict
        Variable values for template rendering.
    """
    result = edit_page(
        page_id=page_id,
        new_body=new_body or None,
        new_title=new_title or None,
        template_name=template_name or None,
        variables=variables or {},
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_append_section
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_append_section(
    page_id: str,
    section_heading: str,
    section_body: str,
    heading_level: int = 2,
) -> list[TextContent]:
    """
    Append a new section to the end of an existing Confluence page.

    Parameters
    ----------
    page_id : str
        Target page ID.
    section_heading : str
        Heading text for the new section.
    section_body : str
        Confluence storage-format HTML for the section content.
    heading_level : int
        Heading level 1-6 (default 2).
    """
    result = append_section(
        page_id=page_id,
        section_heading=section_heading,
        section_body=section_body,
        heading_level=heading_level,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_replace_section
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_replace_section(
    page_id: str,
    section_heading: str,
    new_section_body: str,
    heading_level: int = 2,
) -> list[TextContent]:
    """
    Replace the content of a named section within a Confluence page.

    Parameters
    ----------
    page_id : str
        Target page ID.
    section_heading : str
        Exact heading text of the section to replace.
    new_section_body : str
        New Confluence storage-format HTML for the section content.
    heading_level : int
        Heading level (default 2).
    """
    result = replace_section(
        page_id=page_id,
        section_heading=section_heading,
        new_section_body=new_section_body,
        heading_level=heading_level,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_add_attachment
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_add_attachment(
    page_id: str,
    file_path: str,
    comment: str = "",
) -> list[TextContent]:
    """
    Upload a file as an attachment to a Confluence page.

    Parameters
    ----------
    page_id : str
        Numeric ID of the target page.
    file_path : str
        Absolute path to the file to upload.
    comment : str
        Optional comment stored with this attachment version.
    """
    result = add_attachment(page_id=page_id, file_path=file_path, comment=comment)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_add_multiple_attachments
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_add_multiple_attachments(
    page_id: str,
    file_paths: list[str],
    comment: str = "",
) -> list[TextContent]:
    """
    Upload multiple files as attachments to a Confluence page in one call.

    Parameters
    ----------
    page_id : str
        Numeric ID of the target page.
    file_paths : list[str]
        List of absolute file paths to upload.
    comment : str
        Optional comment applied to all uploaded attachments.
    """
    results = add_multiple_attachments(
        page_id=page_id, file_paths=file_paths, comment=comment
    )
    return [TextContent(type="text", text=json.dumps(results, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_list_attachments
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_list_attachments(page_id: str) -> list[TextContent]:
    """
    List all attachments on a Confluence page.

    Parameters
    ----------
    page_id : str
        Numeric ID of the page.
    """
    result = list_attachments(page_id)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_extract_template
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_extract_template(
    page_id: str,
    template_name: str,
    template_description: str = "",
    save: bool = True,
) -> list[TextContent]:
    """
    Read a live Confluence page and extract a reusable template from it.

    The skill fetches the page, identifies variable content (dates, versions,
    author names, etc.), replaces them with Jinja2 {{ placeholders }}, and
    saves the result as a named template that can be used with
    confluence_create_page.

    Parameters
    ----------
    page_id : str
        ID of the source Confluence page to read.
    template_name : str
        Name to give the extracted template (used when creating pages later).
    template_description : str
        Optional human-readable description for the template.
    save : bool
        If true (default), save the template to TEMPLATE_DIR.
    """
    result = extract_template_from_page(
        page_id=page_id,
        template_name=template_name,
        template_description=template_description,
        save=save,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Tool: confluence_preview_extraction
# ---------------------------------------------------------------------------

@app.tool()
async def confluence_preview_extraction(page_id: str) -> list[TextContent]:
    """
    Dry-run template extraction — show what placeholders would be detected
    without saving any file. Use this before confluence_extract_template
    to verify the extraction looks correct.

    Parameters
    ----------
    page_id : str
        ID of the Confluence page to preview.
    """
    result = preview_template_extraction(page_id)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
