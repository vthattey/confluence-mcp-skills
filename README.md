# confluence-mcp-skills

A Python MCP (Model Context Protocol) server that exposes Confluence REST API operations as tools for **GitHub Copilot** and any other MCP-compatible AI assistant.

Use natural language in Copilot Chat to create pages, edit content, upload attachments, and build reusable page templates — all backed by the Confluence REST API v2.

---

## What it does

| Capability | Description |
|-----------|-------------|
| **Create page from template** | Render a stored template with your variables and publish a new Confluence page |
| **Edit page** | Replace a full page body, append a new section, or surgically replace one section |
| **Add attachments** | Upload one or multiple files to any page |
| **Extract template** | Read any existing Confluence page and automatically generate a reusable template from it |
| **Preview extraction** | Dry-run the template extraction before saving — see exactly what becomes a placeholder |
| **Manage templates** | List and inspect all saved templates and their required variables |

---

## How it works

```
GitHub Copilot (MCP client)
        │
        │  stdio
        ▼
  mcp_server.py              ← this project — runs on your machine
        │
        ▼
  src/confluence_skills/     ← Python business logic
        │
        ▼
  Confluence REST API v2     ← your Atlassian instance
```

The MCP server is a **local process** started by Copilot when you open VS Code. It never requires a hosted service — all protocol communication happens over `stdio` between Copilot and the Python process.

---

## Prerequisites

| Requirement | Version |
|------------|---------|
| Python | 3.11 or later |
| GitHub Copilot | Latest (Chat enabled) |
| Confluence | Cloud or Data Center with REST API v2 |
| Atlassian API token | [Generate here](https://id.atlassian.com/manage-profile/security/api-tokens) |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/confluence-mcp-skills.git
cd confluence-mcp-skills
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
CONFLUENCE_BASE_URL=https://your-org.atlassian.net
CONFLUENCE_EMAIL=your-email@your-org.com
CONFLUENCE_API_TOKEN=your-api-token-here
CONFLUENCE_DEFAULT_SPACE=ENG
TEMPLATE_DIR=templates
```

> **Never commit `.env`** — it is listed in `.gitignore`.

---

## Connecting to GitHub Copilot

### VS Code

Add the `mcp.json` file (already included in the repo) to your VS Code workspace settings, or place it at the project root. Copilot reads it automatically.

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "CONFLUENCE_BASE_URL": "${env:CONFLUENCE_BASE_URL}",
        "CONFLUENCE_EMAIL": "${env:CONFLUENCE_EMAIL}",
        "CONFLUENCE_API_TOKEN": "${env:CONFLUENCE_API_TOKEN}",
        "TEMPLATE_DIR": "templates"
      }
    }
  }
}
```

Restart VS Code. Open Copilot Chat — the tools appear automatically under the `confluence` server.

### Verify the server starts

```bash
python mcp_server.py
```

You should see the server waiting on stdin with no errors. Press `Ctrl+C` to stop.

---

## Available Tools

### `confluence_create_page`

Creates a new Confluence page by rendering a stored template with supplied variable values.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `template_name` | string | Yes | Name of the template (filename without `.json`) |
| `title` | string | Yes | Title of the new page |
| `space_key` | string | Yes | Confluence space key (e.g. `ENG`) |
| `variables` | object | Yes | Key-value pairs for template placeholder substitution |
| `parent_id` | string | No | Parent page ID for nesting |

**Copilot Chat example**

```
Create a new Confluence page in the ENG space using the api_documentation template.
Title: "Order Service API"
Variables:
  api_name: Order Service API
  api_version: 1.0
  base_url: /api/v1/orders
  owner_team: Platform Team
  overview: Manages customer order lifecycle from creation to fulfilment.
  last_updated: 2026-04-24
```

**Returns**

```json
{
  "page_id": "123456",
  "title": "Order Service API",
  "url": "https://your-org.atlassian.net/wiki/spaces/ENG/pages/123456",
  "template_used": "api_documentation",
  "space_key": "ENG"
}
```

---

### `confluence_list_templates`

Lists all templates saved in the `TEMPLATE_DIR` directory.

**Copilot Chat example**

```
What Confluence page templates are available?
```

**Returns**

```json
{
  "templates": ["api_documentation", "meeting_notes", "runbook"]
}
```

---

### `confluence_describe_template`

Returns the metadata and required variables for a named template — use this before creating a page to know what variables to supply.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `template_name` | string | Yes | Template name to inspect |

**Copilot Chat example**

```
What variables does the runbook template need?
```

**Returns**

```json
{
  "name": "runbook",
  "description": "Operational runbook template for services and deployments.",
  "variables": [
    { "name": "service_name", "required": true, "default": "" },
    { "name": "owner_team",   "required": true, "default": "" }
  ]
}
```

---

### `confluence_edit_page`

Replaces the body (and optionally the title) of an existing Confluence page. Accepts either raw Confluence storage-format HTML or a template name and variables.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Numeric ID of the page to update |
| `new_body` | string | No | Raw Confluence storage-format HTML |
| `new_title` | string | No | New page title (keeps existing if omitted) |
| `template_name` | string | No | Template to render as the new body |
| `variables` | object | No | Variable values for template rendering |

> Provide either `new_body` **or** `template_name` + `variables`. If both are given, `new_body` takes precedence.

**Copilot Chat example**

```
Update page 123456 using the runbook template with these values:
  service_name: Payment Service
  service_version: 2.1.0
  owner_team: Payments Team
```

---

### `confluence_append_section`

Appends a new section to the **end** of an existing page without touching the existing content.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Target page ID |
| `section_heading` | string | Yes | Heading text for the new section |
| `section_body` | string | Yes | Confluence storage-format HTML for the section |
| `heading_level` | integer | No | Heading level 1–6 (default: `2`) |

**Copilot Chat example**

```
Append a "Known Issues" section to page 123456 with the content:
"No known issues at this time."
```

---

### `confluence_replace_section`

Finds a section by its heading text and replaces **only that section's content**, leaving the rest of the page unchanged.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Target page ID |
| `section_heading` | string | Yes | Exact heading text of the section to replace |
| `new_section_body` | string | Yes | New content for the section |
| `heading_level` | integer | No | Heading level (default: `2`) |

**Copilot Chat example**

```
Replace the "Rollback Procedure" section on page 123456 with updated steps.
```

---

### `confluence_add_attachment`

Uploads a single file as an attachment to a Confluence page. If an attachment with the same filename already exists, Confluence creates a new version automatically.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Target page ID |
| `file_path` | string | Yes | Absolute path to the file |
| `comment` | string | No | Version comment for the attachment |

**Copilot Chat example**

```
Attach the file /home/user/architecture-diagram.png to Confluence page 123456.
Add comment: "Updated architecture diagram v2"
```

**Returns**

```json
{
  "attachment_id": "att789",
  "file_name": "architecture-diagram.png",
  "file_size_bytes": 204800,
  "media_type": "image/png",
  "page_id": "123456",
  "download_url": "https://your-org.atlassian.net/wiki/download/attachments/123456/architecture-diagram.png"
}
```

---

### `confluence_add_multiple_attachments`

Uploads multiple files in one call. Continues uploading even if one file fails — errors are captured per file in the response.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Target page ID |
| `file_paths` | array | Yes | List of absolute file paths |
| `comment` | string | No | Comment applied to all uploads |

**Copilot Chat example**

```
Upload these files to Confluence page 123456:
- /reports/q1-report.pdf
- /diagrams/flow.png
- /specs/openapi.yaml
```

---

### `confluence_list_attachments`

Lists all attachments currently on a Confluence page.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | Page to inspect |

---

### `confluence_extract_template`

**Reads a live Confluence page and converts it into a reusable template.** This is the core template-creation skill.

The tool:
1. Fetches the page in Confluence storage format (HTML)
2. Walks every text node and replaces dynamic content (dates, versions, author names) with Jinja2 `{{ placeholder }}` tokens
3. Preserves all HTML structure, macros, tables, and formatting exactly
4. Saves the result as a named `.json` template in `TEMPLATE_DIR`

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | ID of the source Confluence page to read |
| `template_name` | string | Yes | Name to give the saved template |
| `template_description` | string | No | Human-readable description |
| `save` | boolean | No | Save to disk (default: `true`) |

**Copilot Chat example**

```
Read Confluence page 98765 and create a reusable template from it.
Save it as "service_design_doc".
```

**Returns**

```json
{
  "template_name": "service_design_doc",
  "saved_path": "templates/service_design_doc.json",
  "variables": [
    { "name": "title",   "required": true  },
    { "name": "date",    "required": false },
    { "name": "version", "required": false }
  ],
  "source_page_id": "98765",
  "source_page_title": "Payment Service Design Doc v1.2",
  "body_preview": "<h1>{{ title }}</h1><p>Last updated: {{ date }}...</p>"
}
```

---

### `confluence_preview_extraction`

Dry-run of `confluence_extract_template` — shows what placeholders would be detected **without saving any file**. Use this first to verify the extraction looks correct before committing.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_id` | string | Yes | ID of the page to preview |

**Copilot Chat example**

```
Preview what template would be extracted from Confluence page 98765 without saving it.
```

---

## Built-in Templates

Three templates are included out of the box under `templates/`.

### `api_documentation`

For REST API technical documentation pages. Pairs with the Java REST API Generator Copilot agent.

**Required variables:** `api_name`, `api_version`, `base_url`, `owner_team`, `overview`, `endpoints_table`, `models_section`

**Optional variables:** `auth_server`, `last_updated`, `error_table`

---

### `meeting_notes`

Standard meeting notes with agenda, decisions, and action items table.

**Required variables:** `meeting_title`, `meeting_date`, `attendees`, `agenda`

**Optional variables:** `facilitator`, `decisions`, `action_items`, `next_meeting`

---

### `runbook`

Operational runbook for services and deployments.

**Required variables:** `service_name`, `service_version`, `owner_team`, `oncall_contact`, `service_overview`, `deployment_steps`, `rollback_steps`

**Optional variables:** `health_check_url`, `known_issues`, `monitoring_links`

---

## Creating Your Own Templates

### Option 1 — Extract from an existing Confluence page (recommended)

```
# In Copilot Chat:
Read page 112233 and save it as a template called "sprint_report"
```

The `confluence_extract_template` tool does the rest.

### Option 2 — Write a template JSON manually

Create a file in `templates/my_template.json`:

```json
{
  "name": "my_template",
  "description": "Description of what this template is for.",
  "variables": [
    { "name": "title",   "description": "Page title",   "required": true,  "default": "" },
    { "name": "author",  "description": "Author name",  "required": false, "default": "Unknown" }
  ],
  "body": "<h1>{{ title }}</h1><p>Author: {{ author }}</p>"
}
```

**Template body rules:**
- Use Jinja2 `{{ variable_name }}` syntax for placeholders
- Body must be valid Confluence storage-format HTML
- Every `{{ variable }}` in the body must have a matching entry in `variables`
- Optional variables with a `default` value do not need to be supplied when creating a page

---

## Running the Tests

```bash
pytest tests/ -v
```

Tests do not make real network calls — the Confluence client is mocked.

```
tests/test_template_engine.py   — template render, save/load, registry
tests/test_read_template.py     — extraction rules, placeholder detection
```

---

## Project Structure

```
confluence-mcp-skills/
├── src/
│   └── confluence_skills/
│       ├── __init__.py
│       ├── client.py           Confluence REST API v2 HTTP client
│       ├── template_engine.py  Template model, Jinja2 rendering, file registry
│       ├── create_page.py      Create page from template
│       ├── edit_page.py        Edit / append / replace-section
│       ├── add_attachment.py   Upload attachments
│       └── read_template.py    Extract template from live page
├── mcp_server.py               MCP server — exposes all tools to Copilot
├── templates/
│   ├── api_documentation.json
│   ├── meeting_notes.json
│   └── runbook.json
├── tests/
│   ├── test_template_engine.py
│   └── test_read_template.py
├── mcp.json                    VS Code MCP server config
├── .github/
│   └── copilot-instructions.md
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

---

## Adding a New Skill

1. Create `src/confluence_skills/<skill_name>.py` with the business logic
2. Expose it as a tool in `mcp_server.py` using `@app.tool()`
3. Add unit tests in `tests/test_<skill_name>.py` — mock `ConfluenceClient`
4. Update this README with the new tool in the **Available Tools** section

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `CONFLUENCE_BASE_URL` not set | `.env` not found | Run `cp .env.example .env` and fill in values |
| `401 Unauthorized` | Wrong email or API token | Regenerate token at [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `404 Space not found` | Wrong space key | Check the key in Confluence URL: `/wiki/spaces/<KEY>/` |
| Tools not visible in Copilot | `mcp.json` not picked up | Restart VS Code after adding `mcp.json` |
| Template not found | Wrong name or directory | Run `confluence_list_templates` to see available names |
| `UndefinedError` on render | Required variable missing | Run `confluence_describe_template` to see what is needed |
| Attachment upload `403` | Missing `X-Atlassian-Token` header | Already handled in client — check API token permissions in Confluence |

---

## License

MIT — see [LICENSE](LICENSE) for details.
