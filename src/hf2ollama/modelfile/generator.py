"""Model family detection and Modelfile generation."""

from __future__ import annotations

import re
from pathlib import Path

from hf2ollama.modelfile.templates import TEMPLATES


def detect_family(filename: str) -> str:
    """Detect model family from GGUF filename."""
    lower = filename.lower()

    if re.search(r"deepseek|ds[-_]?r1", lower):
        return "deepseek"
    if re.search(r"llama[-_]?4", lower):
        return "llama4"
    if re.search(r"llama[-_]?3", lower):
        return "llama3"
    if re.search(r"gemma[-_]?[234]?", lower) and "gemma" in lower:
        return "gemma"
    if re.search(r"qwen|qwq", lower):
        return "qwen"
    if re.search(r"mistral|mixtral|nemo", lower):
        return "mistral"
    if re.search(r"phi[-_]?[34]?", lower) and "phi" in lower:
        return "phi"
    if "granite" in lower:
        return "granite"
    if re.search(r"command[-_]?r|c4ai", lower):
        return "command-r"
    if re.search(r"starcoder|codellama", lower):
        return "qwen"

    return "chatml"


def sanitize_model_name(filename: str) -> str:
    """Generate an Ollama model name from a GGUF filename."""
    base = re.sub(r"\.gguf$", "", filename, flags=re.IGNORECASE)

    quant_match = re.search(r"[-_](Q\d[^.-]*)", base, re.IGNORECASE)
    tag = ""
    if quant_match:
        tag = quant_match.group(1).lower()
        base = base[: quant_match.start()]

    name = re.sub(r"[^a-z0-9._-]", "-", base.lower())
    name = re.sub(r"-+", "-", name).strip("-")

    if tag:
        name = f"{name}:{tag}"

    return name


def generate_modelfile(
    gguf_path: str,
    family: str | None = None,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """Generate an Ollama Modelfile for a GGUF file."""
    filename = Path(gguf_path).name

    if family is None:
        family = detect_family(filename)

    tmpl = TEMPLATES.get(family, TEMPLATES["chatml"])

    lines = [
        f"FROM ./{filename}",
        "",
        f'TEMPLATE """{tmpl.template}"""',
        "",
    ]

    for stop in tmpl.stop_tokens:
        lines.append(f'PARAMETER stop "{stop}"')

    lines.extend(
        [
            "",
            f"PARAMETER temperature {temperature}",
            f"PARAMETER top_p {top_p}",
        ]
    )

    return "\n".join(lines)
