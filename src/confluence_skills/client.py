"""Confluence REST API v2 client — all HTTP calls go through this module."""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class ConfluenceError(Exception):
    """Raised when the Confluence API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Confluence API error {status_code}: {message}")


class ConfluenceClient:
    """Thin wrapper around the Confluence REST API v2."""

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ["CONFLUENCE_BASE_URL"]).rstrip("/")
        self._session = requests.Session()
        self._session.auth = (
            email or os.environ["CONFLUENCE_EMAIL"],
            api_token or os.environ["CONFLUENCE_API_TOKEN"],
        )
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def get_page(self, page_id: str, body_format: str = "storage") -> dict[str, Any]:
        """Return page metadata and body content."""
        url = f"{self._base_url}/wiki/api/v2/pages/{page_id}"
        return self._get(url, params={"body-format": body_format})

    def get_page_by_title(
        self, space_key: str, title: str, body_format: str = "storage"
    ) -> dict[str, Any] | None:
        """Return the first page matching title in the given space, or None."""
        url = f"{self._base_url}/wiki/api/v2/pages"
        params = {"spaceKey": space_key, "title": title, "body-format": body_format}
        result = self._get(url, params=params)
        results = result.get("results", [])
        return results[0] if results else None

    def create_page(
        self,
        space_id: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        body_format: str = "storage",
    ) -> dict[str, Any]:
        """Create a new Confluence page and return the created page object."""
        url = f"{self._base_url}/wiki/api/v2/pages"
        payload: dict[str, Any] = {
            "spaceId": space_id,
            "title": title,
            "body": {"representation": body_format, "value": body},
        }
        if parent_id:
            payload["parentId"] = parent_id
        return self._post(url, json=payload)

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: int,
        body_format: str = "storage",
    ) -> dict[str, Any]:
        """Update an existing page (version must be current version + 1)."""
        url = f"{self._base_url}/wiki/api/v2/pages/{page_id}"
        payload: dict[str, Any] = {
            "id": page_id,
            "title": title,
            "version": {"number": version},
            "body": {"representation": body_format, "value": body},
        }
        return self._put(url, json=payload)

    def get_page_version(self, page_id: str) -> int:
        """Return the current version number of a page."""
        page = self.get_page(page_id)
        return page["version"]["number"]

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def add_attachment(
        self,
        page_id: str,
        file_path: str,
        comment: str = "",
    ) -> dict[str, Any]:
        """Upload a file as an attachment to a page."""
        url = f"{self._base_url}/wiki/api/v2/pages/{page_id}/attachments"
        file_name = os.path.basename(file_path)

        # Attachment upload requires multipart — override Content-Type for this call
        headers = {"X-Atlassian-Token": "no-check"}
        with open(file_path, "rb") as fh:
            files = {"file": (file_name, fh)}
            data = {"comment": comment} if comment else {}
            response = self._session.post(url, headers=headers, files=files, data=data)

        self._raise_for_status(response)
        return response.json()

    def list_attachments(self, page_id: str) -> list[dict[str, Any]]:
        """Return all attachments on a page."""
        url = f"{self._base_url}/wiki/api/v2/pages/{page_id}/attachments"
        return self._get(url).get("results", [])

    # ------------------------------------------------------------------
    # Spaces
    # ------------------------------------------------------------------

    def get_space_id(self, space_key: str) -> str:
        """Resolve a space key (e.g. 'ENG') to its numeric space ID."""
        url = f"{self._base_url}/wiki/api/v2/spaces"
        result = self._get(url, params={"keys": space_key})
        results = result.get("results", [])
        if not results:
            raise ConfluenceError(404, f"Space '{space_key}' not found")
        return results[0]["id"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict | None = None) -> dict[str, Any]:
        response = self._session.get(url, params=params)
        self._raise_for_status(response)
        return response.json()

    def _post(self, url: str, json: dict) -> dict[str, Any]:
        response = self._session.post(url, json=json)
        self._raise_for_status(response)
        return response.json()

    def _put(self, url: str, json: dict) -> dict[str, Any]:
        response = self._session.put(url, json=json)
        self._raise_for_status(response)
        return response.json()

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if not response.ok:
            try:
                detail = response.json().get("message", response.text)
            except Exception:
                detail = response.text
            raise ConfluenceError(response.status_code, detail)
