"""HuggingFace API client - search repos and list GGUF files."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import httpx

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api"


@dataclass
class RepoInfo:
    """Metadata for a HuggingFace model repository."""

    repo_id: str
    downloads: int
    likes: int
    last_modified: str


@dataclass
class GGUFFile:
    """A GGUF file in a HuggingFace repository."""

    filename: str
    size_bytes: int
    repo_id: str

    @property
    def size_gb(self) -> float:
        """Return file size in gigabytes."""
        return self.size_bytes / (1024**3)

    @property
    def size_display(self) -> str:
        """Return human-readable size string."""
        if self.size_bytes >= 1024**3:
            return f"{self.size_gb:.1f} GB"
        return f"{self.size_bytes / (1024**2):.0f} MB"


@contextmanager
def _get_client(client: httpx.Client | None) -> Iterator[httpx.Client]:
    """Yield an httpx client, creating one if not provided."""
    if client is not None:
        yield client
    else:
        owned = httpx.Client(timeout=15.0)
        try:
            yield owned
        finally:
            owned.close()


def search_gguf_repos(
    query: str,
    limit: int = 20,
    sort: str = "downloads",
    client: httpx.Client | None = None,
) -> list[RepoInfo]:
    """Search HuggingFace for GGUF model repos.

    Parameters
    ----------
    query : str
        Search query string.
    limit : int
        Maximum number of results.
    sort : str
        Sort field (downloads, likes, lastModified).
    client : httpx.Client | None
        Optional shared HTTP client.

    Returns
    -------
    list[RepoInfo]
        Matching repositories sorted by the given field.

    """
    with _get_client(client) as c:
        params = {
            "search": query,
            "filter": "gguf",
            "sort": sort,
            "direction": "-1",
            "limit": str(limit),
        }
        resp = c.get(f"{HF_API_BASE}/models", params=params)
        resp.raise_for_status()

        results: list[RepoInfo] = []
        for item in resp.json():
            results.append(
                RepoInfo(
                    repo_id=item.get("id", ""),
                    downloads=item.get("downloads", 0),
                    likes=item.get("likes", 0),
                    last_modified=item.get("lastModified", ""),
                )
            )
        logger.debug("Search '%s' returned %d results", query, len(results))
        return results


def list_gguf_files(
    repo_id: str,
    client: httpx.Client | None = None,
) -> list[GGUFFile]:
    """List GGUF files in a HuggingFace repo with their sizes.

    Parameters
    ----------
    repo_id : str
        HuggingFace repo (e.g., bartowski/Qwen2.5-Coder-7B-Instruct-GGUF).
    client : httpx.Client | None
        Optional shared HTTP client.

    Returns
    -------
    list[GGUFFile]
        GGUF files sorted by size ascending.

    """
    with _get_client(client) as c:
        resp = c.get(f"{HF_API_BASE}/models/{repo_id}/tree/main")
        resp.raise_for_status()

        files: list[GGUFFile] = []
        for item in resp.json():
            path: str = item.get("path", "")
            if path.lower().endswith(".gguf"):
                files.append(
                    GGUFFile(
                        filename=path,
                        size_bytes=item.get("size", 0),
                        repo_id=repo_id,
                    )
                )
        logger.debug("Repo '%s' has %d GGUF files", repo_id, len(files))
        return sorted(files, key=lambda f: f.size_bytes)


def find_gguf_by_quant(
    repo_id: str,
    quant: str = "Q4_K_M",
    client: httpx.Client | None = None,
) -> GGUFFile | None:
    """Find a specific quantization in a repo.

    Parameters
    ----------
    repo_id : str
        HuggingFace repo ID.
    quant : str
        Quantization level to match in the filename.
    client : httpx.Client | None
        Optional shared HTTP client.

    Returns
    -------
    GGUFFile | None
        Matching file, or None if not found.

    """
    files = list_gguf_files(repo_id, client=client)
    quant_lower = quant.lower()

    for f in files:
        if quant_lower in f.filename.lower():
            return f

    return None


def get_download_url(repo_id: str, filename: str) -> str:
    """Build the direct download URL for a file.

    Parameters
    ----------
    repo_id : str
        HuggingFace repo ID.
    filename : str
        Name of the file to download.

    Returns
    -------
    str
        Direct download URL.

    """
    return f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
