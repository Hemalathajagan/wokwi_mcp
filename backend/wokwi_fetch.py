"""
Fetches Wokwi Arduino project files (diagram.json + sketch) from the Wokwi REST API.
"""

import io
import json
import re
import zipfile
from dataclasses import dataclass, field

import httpx


@dataclass
class WokwiProject:
    project_id: str
    diagram: dict
    sketch_code: str
    other_files: dict = field(default_factory=dict)


def extract_project_id(url: str) -> str:
    """Extract numeric project ID from a Wokwi URL.

    Supports formats:
      - https://wokwi.com/projects/123456
      - https://wokwi.com/projects/123456/fullscreen
      - https://wokwi.com/projects/123456?param=value
    """
    match = re.search(r"/projects/(\d+)", url)
    if not match:
        raise ValueError(
            f"Cannot extract project ID from URL: {url}. "
            "Expected format: https://wokwi.com/projects/<numeric_id>"
        )
    return match.group(1)


async def fetch_project(url: str) -> WokwiProject:
    """Fetch a public Wokwi project by URL.

    Retrieves diagram.json and all project files (sketch, libraries, etc.)
    from the Wokwi REST API.

    Raises:
        ValueError: If the URL format is invalid.
        httpx.HTTPStatusError: If the project is private (403) or not found (404).
    """
    project_id = extract_project_id(url)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Fetch diagram.json
        diagram_resp = await client.get(
            f"https://wokwi.com/api/projects/{project_id}/diagram.json"
        )
        if diagram_resp.status_code == 403:
            raise ValueError(
                f"Project {project_id} is private. Only public projects can be analyzed."
            )
        if diagram_resp.status_code == 404:
            raise ValueError(f"Project {project_id} not found. Check the URL and try again.")
        diagram_resp.raise_for_status()
        diagram = diagram_resp.json()

        # Fetch ZIP for sketch and other files
        sketch_code = ""
        other_files = {}

        try:
            zip_resp = await client.get(
                f"https://wokwi.com/api/projects/{project_id}/zip"
            )
            zip_resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                for name in zf.namelist():
                    content = zf.read(name).decode("utf-8", errors="replace")
                    if name.endswith(".ino") or name.endswith(".cpp") and not sketch_code:
                        sketch_code = content
                    elif name == "diagram.json":
                        continue  # already fetched separately
                    else:
                        other_files[name] = content
        except (httpx.HTTPStatusError, zipfile.BadZipFile):
            # ZIP endpoint may not be available for all projects
            pass

    return WokwiProject(
        project_id=project_id,
        diagram=diagram,
        sketch_code=sketch_code,
        other_files=other_files,
    )


async def fetch_diagram_only(url: str) -> dict:
    """Fetch only the diagram.json for a Wokwi project."""
    project_id = extract_project_id(url)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(
            f"https://wokwi.com/api/projects/{project_id}/diagram.json"
        )
        resp.raise_for_status()
        return resp.json()
