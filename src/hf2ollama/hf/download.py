"""Standard download with httpx - resumable, with progress bar."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from hf2ollama.hf.api import _get_client

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=10.0)


def download_file(
    url: str,
    dest_path: str,
    client: httpx.Client | None = None,
    chunk_size: int = 4 * 1024 * 1024,
) -> Path:
    """Download a file with resume support and progress bar.

    Parameters
    ----------
    url : str
        Direct download URL.
    dest_path : str
        Local path to write the file.
    client : httpx.Client | None
        Optional shared HTTP client. Creates one if not provided.
    chunk_size : int
        Download chunk size in bytes (default 4MB).

    Returns
    -------
    Path
        Path to the downloaded file.

    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with _get_client(client) as c:
        existing_size: int = dest.stat().st_size if dest.exists() else 0

        headers: dict[str, str] = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"
            logger.info("Resuming download from byte %d", existing_size)

        with c.stream("GET", url, headers=headers, follow_redirects=True) as resp:
            if resp.status_code == 416:
                logger.info("File already fully downloaded: %s", dest)
                return dest

            resp.raise_for_status()

            total_size: int | None = None
            if resp.status_code == 206:
                content_range = resp.headers.get("content-range", "")
                if "/" in content_range:
                    total_size = int(content_range.split("/")[-1])
                mode = "ab"
            else:
                cl = resp.headers.get("content-length")
                total_size = int(cl) if cl else None
                existing_size = 0
                mode = "wb"

            progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
            )

            filename = Path(url.split("/")[-1].split("?")[0]).name
            with progress:
                task = progress.add_task(
                    filename[:40],
                    total=total_size,
                    completed=existing_size,
                )

                with open(dest, mode) as f:
                    for chunk in resp.iter_bytes(chunk_size=chunk_size):
                        f.write(chunk)
                        progress.advance(task, len(chunk))

        return dest


def validate_file_size(path: str, expected_size: int) -> bool:
    """Check if downloaded file matches expected size.

    Parameters
    ----------
    path : str
        Path to the downloaded file.
    expected_size : int
        Expected file size in bytes.

    Returns
    -------
    bool
        True if file size matches.

    """
    actual = Path(path).stat().st_size
    return actual == expected_size
