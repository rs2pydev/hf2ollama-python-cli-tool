"""Configuration management - persistent settings in ~/.hf2ollama/config.toml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


CONFIG_DIR = Path.home() / ".hf2ollama"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DEFAULT_DOWNLOAD_DIR = CONFIG_DIR / "downloads"


@dataclass
class Config:
    """Persistent user configuration for hf2ollama."""

    download_dir: str = str(DEFAULT_DOWNLOAD_DIR)
    proxy: str | None = None
    no_proxy: str | None = None
    hf_token: str | None = None
    hf_endpoint: str | None = None
    default_quant: str = "Q4_K_M"


def load_config() -> Config:
    """Load config from file, falling back to defaults."""
    if not CONFIG_FILE.exists():
        return Config()

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    return Config(
        download_dir=data.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)),
        proxy=data.get("proxy"),
        no_proxy=data.get("no_proxy"),
        hf_token=data.get("hf_token") or os.environ.get("HF_TOKEN"),
        hf_endpoint=data.get("hf_endpoint"),
        default_quant=data.get("default_quant", "Q4_K_M"),
    )


def save_config(config: Config) -> None:
    """Save config to TOML file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f'download_dir = "{config.download_dir}"')
    lines.append(f'default_quant = "{config.default_quant}"')
    if config.proxy:
        lines.append(f'proxy = "{config.proxy}"')
    if config.no_proxy:
        lines.append(f'no_proxy = "{config.no_proxy}"')
    if config.hf_token:
        lines.append(f'hf_token = "{config.hf_token}"')
    if config.hf_endpoint:
        lines.append(f'hf_endpoint = "{config.hf_endpoint}"')

    CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_download_dir(config: Config) -> Path:
    """Create and return the download directory."""
    dl_dir = Path(config.download_dir)
    dl_dir.mkdir(parents=True, exist_ok=True)
    return dl_dir
