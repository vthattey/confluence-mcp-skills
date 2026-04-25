"""Skill: add or replace file attachments on a Confluence page."""

import os
from typing import Any

from .client import ConfluenceClient


def add_attachment(
    page_id: str,
    file_path: str,
    comment: str = "",
) -> dict[str, Any]:
    """
    Upload a file as an attachment to a Confluence page.

    If an attachment with the same filename already exists on the page,
    Confluence replaces it automatically (new version).

    Parameters
    ----------
    page_id : str
        Numeric ID of the target page.
    file_path : str
        Absolute or relative path to the file to upload.
    comment : str
        Optional comment stored with the attachment version.

    Returns
    -------
    dict
        {
          "attachment_id": str,
          "file_name": str,
          "file_size_bytes": int,
          "media_type": str,
          "page_id": str,
          "download_url": str,
        }
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    client = ConfluenceClient()
    result = client.add_attachment(page_id=page_id, file_path=file_path, comment=comment)

    # The API returns a results list even for single-file uploads
    attachment = result["results"][0] if "results" in result else result

    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
    download_path = attachment.get("_links", {}).get("download", "")

    return {
        "attachment_id": attachment["id"],
        "file_name": attachment["title"],
        "file_size_bytes": attachment.get("extensions", {}).get("fileSize", 0),
        "media_type": attachment.get("extensions", {}).get("mediaType", ""),
        "page_id": page_id,
        "download_url": f"{base_url}{download_path}" if download_path else "",
    }


def add_multiple_attachments(
    page_id: str,
    file_paths: list[str],
    comment: str = "",
) -> list[dict[str, Any]]:
    """
    Upload multiple files to a page in one call.

    Returns a list of attachment result dicts, one per file.
    Continues uploading remaining files even if one fails —
    errors are captured in the result dict under the key 'error'.
    """
    results = []
    for path in file_paths:
        try:
            result = add_attachment(page_id=page_id, file_path=path, comment=comment)
        except Exception as exc:
            result = {"file_path": path, "error": str(exc)}
        results.append(result)
    return results


def list_attachments(page_id: str) -> list[dict[str, Any]]:
    """
    Return a summary list of all attachments on a page.

    Returns
    -------
    list of dict
        [{"attachment_id", "file_name", "media_type", "file_size_bytes", "download_url"}, ...]
    """
    client = ConfluenceClient()
    raw = client.list_attachments(page_id)
    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")

    return [
        {
            "attachment_id": a["id"],
            "file_name": a["title"],
            "media_type": a.get("extensions", {}).get("mediaType", ""),
            "file_size_bytes": a.get("extensions", {}).get("fileSize", 0),
            "download_url": f"{base_url}{a.get('_links', {}).get('download', '')}",
        }
        for a in raw
    ]
