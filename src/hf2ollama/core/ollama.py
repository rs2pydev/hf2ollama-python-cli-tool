"""Ollama binary interaction - find, create, list, remove models."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OllamaModel:
    """Metadata for a locally installed Ollama model."""

    name: str
    size: str
    modified: str
    model_id: str = ""


def find_ollama() -> str:
    """Find the ollama executable."""
    if os.name == "nt":
        local_path = (
            Path(os.environ.get("USERPROFILE", "")) / "AppData/Local/Programs/Ollama/ollama.exe"
        )
        if local_path.exists():
            return str(local_path)

    found = shutil.which("ollama")
    if found:
        return found

    raise FileNotFoundError("Ollama not found. Install from https://ollama.com/download")


def create_model(
    name: str,
    modelfile_path: str,
    working_dir: str | None = None,
) -> str:
    """Run `ollama create` with a Modelfile."""
    ollama = find_ollama()
    cwd = working_dir or str(Path(modelfile_path).parent)

    result = subprocess.run(
        [ollama, "create", name, "-f", "Modelfile"],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ollama create failed: {result.stderr or result.stdout}")

    return result.stdout.strip()


def list_models() -> list[OllamaModel]:
    """List locally installed Ollama models."""
    ollama = find_ollama()

    result = subprocess.run(
        [ollama, "list"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ollama list failed: {result.stderr}")

    models = []
    lines = result.stdout.strip().splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 3:
            models.append(
                OllamaModel(
                    name=parts[0],
                    model_id=parts[1] if len(parts) > 1 else "",
                    size=parts[2]
                    + (" " + parts[3] if len(parts) > 3 and parts[3] in ("MB", "GB", "KB") else ""),
                    modified=" ".join(parts[4:]) if len(parts) > 4 else "",
                )
            )
    return models


def remove_model(name: str) -> str:
    """Remove an Ollama model."""
    ollama = find_ollama()

    result = subprocess.run(
        [ollama, "rm", name],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ollama rm failed: {result.stderr}")

    return result.stdout.strip()


def show_model(name: str) -> str:
    """Show model details."""
    ollama = find_ollama()

    result = subprocess.run(
        [ollama, "show", name],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ollama show failed: {result.stderr}")

    return result.stdout.strip()


def model_exists(name: str) -> bool:
    """Check if a model is already installed."""
    try:
        models = list_models()
        base_name = name.split(":")[0]
        return any(base_name in m.name for m in models)
    except (RuntimeError, FileNotFoundError, subprocess.SubprocessError) as e:
        logger.debug("model_exists check failed: %s", e)
        return False
