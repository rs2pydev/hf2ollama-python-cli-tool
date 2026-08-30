# hf2ollama

A Python CLI tool that searches, downloads, and imports HuggingFace GGUF models into Ollama. Handles model discovery, quantization selection, automatic Modelfile generation, and resumable downloads.

## What it does

`ollama pull` only works with models hosted on the Ollama registry. Most open-weight GGUF models live on HuggingFace. This tool bridges that gap: search HuggingFace for GGUF repos, pick a quantization, download the file, auto-generate the correct Modelfile with chat template and stop tokens, and import into Ollama - all in one command.

It also handles a common Python SSL issue where `certifi` (the default CA bundle) doesn't include certificates from the operating system's trust store. The `--ssl-fix` flag exports the OS certificate store and configures Python to use it.

## Installation

Works on Windows, macOS, and Linux. Requires Python 3.10+.

```shell
pip install hf2ollama
```

From source:

```shell
git clone https://github.com/rs2pydev/hf2ollama-python-cli-tool.git
cd hf2ollama-python-cli-tool
pip install -e ".[dev]"
```

## Quick start

```shell
# Search for models
hf2ollama search "qwen 7b gguf"

# See available quantizations and file sizes
hf2ollama list-files bartowski/Qwen2.5-Coder-7B-Instruct-GGUF

# Download and import into Ollama
hf2ollama pull bartowski/Qwen2.5-Coder-7B-Instruct-GGUF --quant Q4_K_M

# Fix Python SSL certificate issues if downloads fail
hf2ollama pull bartowski/Qwen2.5-Coder-7B-Instruct-GGUF --ssl-fix

# Use alternative download method (Windows, PowerShell 7 required)
hf2ollama pull bartowski/Qwen2.5-Coder-7B-Instruct-GGUF --alt-download
```

## Commands

### pull

Download a GGUF model from HuggingFace and import into Ollama.

```shell
hf2ollama pull <repo> [--quant Q4_K_M] [--name my-model] [--keep-gguf] [--ssl-fix] [--alt-download]
```

Options:

- `--quant` / `-q` - Quantization level (Q2_K, Q3_K_M, Q4_K_M, Q5_K_M, Q6_K, Q8_0). Default: Q4_K_M.
- `--name` / `-n` - Ollama model name. Auto-generated from filename if not specified.
- `--keep-gguf` - Keep the GGUF file after importing into Ollama.
- `--ssl-fix` - Use OS certificate store instead of Python's default CA bundle.
- `--alt-download` - Use alternative PowerShell-based download method (Windows only, requires PowerShell 7).

The tool auto-detects the model family from the filename and generates the correct Modelfile with chat template and stop tokens.

### search

Search HuggingFace for GGUF model repositories.

```shell
hf2ollama search "llama 70b" --limit 20 --sort downloads
```

### list-files

Show available GGUF files in a repository with their sizes.

```shell
hf2ollama list-files bartowski/Qwen2.5-Coder-7B-Instruct-GGUF
```

### list

List locally installed Ollama models.

```shell
hf2ollama list
```

### remove

Delete an Ollama model.

```shell
hf2ollama remove my-model:q4_k_m
```

### info

Show details about an installed Ollama model.

```shell
hf2ollama info my-model:q4_k_m
```

### recommend

Recommend quantization based on your GPU VRAM and model size.

```shell
# Auto-detect GPU VRAM
hf2ollama recommend --params 7

# Specify VRAM manually
hf2ollama recommend --params 70 --vram 24
```

### network-check

Check whether HuggingFace is reachable and whether SSL certificates are configured correctly.

```shell
hf2ollama network-check
```

## Supported model families

The tool auto-detects model families from GGUF filenames and generates the correct Ollama Modelfile:

- Llama 3 / 3.1 / 3.2 / 3.3 / 4
- Gemma (2, 3, 4)
- Qwen (2, 2.5, 3)
- Mistral / Mixtral
- Phi (3, 4)
- DeepSeek (R1, V3)
- Granite
- Command-R
- ChatML (fallback for unrecognized models)

## Supported quantizations

Q2_K, Q3_K_M, Q4_K_M (default), Q5_K_M, Q6_K, Q8_0

## Configuration

Persistent config is stored in `~/.hf2ollama/config.toml`:

```toml
download_dir = "C:/Users/you/.hf2ollama/downloads"
default_quant = "Q4_K_M"
hf_token = "hf_xxxxx"
```

## Requirements

- Python 3.10+
- Ollama installed locally
- For `--alt-download`: Windows + PowerShell 7

## Dependencies

- click - CLI framework
- httpx - HTTP client with resumable downloads
- rich - Terminal tables and progress bars
- truststore - OS certificate store access
- certifi - Public CA bundle

## License

MIT
