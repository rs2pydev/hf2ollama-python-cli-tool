"""Alternative download method using embedded PowerShell script (Windows only)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def is_alt_download_available() -> bool:
    """Check if the PowerShell-based download method is available."""
    if sys.platform != "win32":
        return False

    pwsh = shutil.which("pwsh")
    return pwsh is not None


def get_script_path() -> Path:
    """Get path to the embedded HfDownload.ps1 script."""
    script_dir = Path(__file__).parent.parent / "scripts"
    return script_dir / "HfDownload.ps1"


def alt_download(
    repo: str,
    filename: str,
    out_dir: str,
) -> Path:
    """Download a file using the PowerShell-based download method.

    Requires Windows and PowerShell 7 (pwsh).

    Raises RuntimeError if the download fails or prerequisites are not met.
    """
    if not is_alt_download_available():
        raise RuntimeError(
            "Alternative download requires Windows + PowerShell 7 (pwsh)."
        )

    script = get_script_path()
    if not script.exists():
        raise RuntimeError(f"HfDownload.ps1 not found at {script}")

    cmd = [
        "pwsh",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Repo",
        repo,
        "-File",
        filename,
        "-OutDir",
        out_dir,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=3600,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Alternative download failed: {stderr or result.stdout}")

    dest = Path(out_dir) / filename
    if not dest.exists():
        raise RuntimeError(f"Download completed but file not found at {dest}")

    return dest
