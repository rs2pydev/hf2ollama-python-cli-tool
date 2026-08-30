"""Click-based CLI for hf2ollama."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from hf2ollama import __version__

console = Console()


@click.group()
@click.version_option(__version__, prog_name="hf2ollama")
def main() -> None:
    """Search, download, and import HuggingFace GGUF models into Ollama."""


@main.command()
@click.argument("repo")
@click.option(
    "--quant", "-q", default=None, help="Quantization (Q2_K, Q3_K_M, Q4_K_M, Q5_K_M, Q6_K, Q8_0)."
)
@click.option(
    "--name", "-n", default=None, help="Ollama model name. Auto-generated if not specified."
)
@click.option("--keep-gguf", is_flag=True, help="Keep the GGUF file after import.")
@click.option(
    "--alt-download", is_flag=True, help="Use alternative PowerShell download (Windows only)."
)
@click.option("--ssl-fix", is_flag=True, help="Use OS certificate store for SSL verification.")
def pull(
    repo: str,
    quant: str | None,
    name: str | None,
    keep_gguf: bool,
    alt_download: bool,
    ssl_fix: bool,
) -> None:
    """Download a GGUF model and import into Ollama.

    REPO is a HuggingFace repo ID (e.g., bartowski/Qwen2.5-Coder-7B-Instruct-GGUF).
    """
    from hf2ollama.core.config import ensure_download_dir, load_config
    from hf2ollama.core.ollama import create_model, find_ollama
    from hf2ollama.hf.api import find_gguf_by_quant, get_download_url, list_gguf_files
    from hf2ollama.hf.download import download_file, validate_file_size
    from hf2ollama.modelfile.generator import (
        detect_family,
        generate_modelfile,
        sanitize_model_name,
    )
    from hf2ollama.network.ssl_fix import apply_ssl_fix

    config = load_config()
    resolved_quant = quant or config.default_quant

    if ssl_fix:
        console.print("[dim]Configuring SSL certificates...[/dim]")
        apply_ssl_fix(proxy=config.proxy)

    try:
        find_ollama()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    console.print(f"[bold]Searching for {resolved_quant} in {repo}...[/bold]")

    import httpx

    try:
        client = httpx.Client(timeout=15.0)
        gguf = find_gguf_by_quant(repo, resolved_quant, client=client)

        if gguf is None:
            console.print(f"[yellow]No {resolved_quant} file found. Available files:[/yellow]")
            files = list_gguf_files(repo, client=client)
            for f in files:
                console.print(f"  {f.filename} ({f.size_display})")
            client.close()
            raise SystemExit(1)

        console.print(f"[green]Found:[/green] {gguf.filename} ({gguf.size_display})")

        dl_dir = ensure_download_dir(config)
        dest = dl_dir / gguf.filename
        url = get_download_url(repo, gguf.filename)

        if alt_download:
            from hf2ollama.hf.alt_download import alt_download as _alt_dl

            console.print("[bold yellow]Using alternative download method...[/bold yellow]")
            dest = _alt_dl(repo, gguf.filename, str(dl_dir))
        else:
            console.print("[dim]Downloading...[/dim]")
            dest = download_file(url, str(dest), client=client)

        client.close()

        if not validate_file_size(str(dest), gguf.size_bytes):
            console.print("[red]File size mismatch - download may be incomplete.[/red]")
            raise SystemExit(1)

    except httpx.ConnectError as e:
        err = str(e).lower()
        if "ssl" in err or "certificate" in err:
            console.print("[red]SSL certificate error.[/red]")
            console.print("Try: [bold]hf2ollama pull --ssl-fix <repo>[/bold]")
        else:
            console.print(f"[red]Connection error: {e}[/red]")
        raise SystemExit(1)

    model_name = name or sanitize_model_name(gguf.filename)
    family = detect_family(gguf.filename)
    console.print(f"[dim]Detected family: {family}[/dim]")

    modelfile_content = generate_modelfile(str(dest), family=family)
    modelfile_path = dest.parent / "Modelfile"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")

    console.print(f"[bold]Creating Ollama model: {model_name}[/bold]")
    try:
        output = create_model(model_name, str(modelfile_path))
        console.print(f"[green]{output}[/green]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    modelfile_path.unlink(missing_ok=True)
    if not keep_gguf:
        dest.unlink(missing_ok=True)
        console.print("[dim]Cleaned up GGUF file.[/dim]")

    console.print(f"\n[bold green]Done![/bold green] Run: [bold]ollama run {model_name}[/bold]")


@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=15, help="Max results.")
@click.option(
    "--sort", "-s", default="downloads", type=click.Choice(["downloads", "likes", "lastModified"])
)
@click.option("--ssl-fix", is_flag=True, help="Use OS certificate store.")
def search(query: str, limit: int, sort: str, ssl_fix: bool) -> None:
    """Search HuggingFace for GGUF model repos."""
    from hf2ollama.hf.api import search_gguf_repos
    from hf2ollama.network.ssl_fix import apply_ssl_fix

    if ssl_fix:
        apply_ssl_fix()

    results = search_gguf_repos(query, limit=limit, sort=sort)

    if not results:
        console.print("[yellow]No GGUF repos found.[/yellow]")
        return

    table = Table(title=f"GGUF repos matching '{query}'")
    table.add_column("Repository", style="bold")
    table.add_column("Downloads", justify="right")
    table.add_column("Likes", justify="right")

    for r in results:
        table.add_row(r.repo_id, f"{r.downloads:,}", str(r.likes))

    console.print(table)


@main.command("list-files")
@click.argument("repo")
@click.option("--ssl-fix", is_flag=True, help="Use OS certificate store.")
def list_files(repo: str, ssl_fix: bool) -> None:
    """List GGUF files in a HuggingFace repo."""
    from hf2ollama.hf.api import list_gguf_files
    from hf2ollama.network.ssl_fix import apply_ssl_fix

    if ssl_fix:
        apply_ssl_fix()

    files = list_gguf_files(repo)

    if not files:
        console.print(f"[yellow]No GGUF files found in {repo}.[/yellow]")
        return

    table = Table(title=f"GGUF files in {repo}")
    table.add_column("File", style="bold")
    table.add_column("Size", justify="right")

    for f in files:
        table.add_row(f.filename, f.size_display)

    console.print(table)


@main.command("list")
def list_models() -> None:
    """List locally installed Ollama models."""
    from hf2ollama.core.ollama import list_models as _list

    try:
        models = _list()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    if not models:
        console.print("[yellow]No Ollama models installed.[/yellow]")
        return

    table = Table(title="Ollama Models")
    table.add_column("Name", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Modified")

    for m in models:
        table.add_row(m.name, m.size, m.modified)

    console.print(table)


@main.command()
@click.argument("model_name")
def remove(model_name: str) -> None:
    """Remove an Ollama model."""
    from hf2ollama.core.ollama import remove_model

    try:
        remove_model(model_name)
        console.print(f"[green]Removed: {model_name}[/green]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


@main.command()
@click.argument("model_name")
def info(model_name: str) -> None:
    """Show details about an Ollama model."""
    from hf2ollama.core.ollama import show_model

    try:
        output = show_model(model_name)
        console.print(output)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


@main.command()
@click.option(
    "--vram", type=float, default=None, help="Available VRAM in GB. Auto-detected if not specified."
)
@click.option(
    "--params", "-p", type=float, required=True,
    help="Model parameter count in billions (e.g., 7 for 7B).",
)
def recommend(vram: float | None, params: float) -> None:
    """Recommend quantization based on VRAM and model size."""
    from hf2ollama.utils.vram import detect_vram, recommend_quant

    if vram is None:
        vram_info = detect_vram()
        if vram_info:
            vram = vram_info.available_gb
            console.print(f"[dim]Detected: {vram_info.gpu_name} ({vram:.1f} GB)[/dim]")
        else:
            console.print("[yellow]Could not detect GPU. Specify --vram manually.[/yellow]")
            raise SystemExit(1)

    fits = recommend_quant(params, vram)

    if not fits:
        console.print(
            f"[red]No quantization of a {params}B model fits in {vram:.1f} GB VRAM.[/red]"
        )
        console.print(f"[dim]Smallest (Q2_K) needs ~{params * 0.31 * 1.1:.1f} GB.[/dim]")
        return

    table = Table(title=f"Quantizations for {params}B model ({vram:.1f} GB VRAM)")
    table.add_column("Quantization")
    table.add_column("Est. Size", justify="right")
    table.add_column("Fits?", justify="center")

    from hf2ollama.utils.vram import QUANT_MULTIPLIERS

    for quant, mult in sorted(QUANT_MULTIPLIERS.items(), key=lambda x: x[1]):
        est = params * mult * 1.1
        fits_str = "[green]Yes[/green]" if est <= vram else "[red]No[/red]"
        table.add_row(quant, f"{est:.1f} GB", fits_str)

    console.print(table)
    console.print(f"\n[bold]Recommended:[/bold] {fits[-1]} (largest that fits)")


@main.command("network-check")
def network_check() -> None:
    """Check HuggingFace reachability and SSL certificate status."""
    from hf2ollama.network.detect import check_network

    console.print("[bold]Checking network...[/bold]\n")
    status = check_network()

    table = Table(title="Network Diagnostics")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    hf_status = "[green]OK[/green]" if status.hf_reachable else "[red]UNREACHABLE[/red]"
    table.add_row("HuggingFace reachable", hf_status, status.hf_error or "Connected")

    ssl_status = "[green]OK[/green]" if status.hf_ssl_ok else "[red]FAIL[/red]"
    table.add_row(
        "SSL certificates",
        ssl_status,
        f"{status.cert_count} system certs" if status.system_certs_available else "Limited certs",
    )

    proxy_status = "[green]Set[/green]" if status.proxy_configured else "[dim]None[/dim]"
    table.add_row("Proxy configured", proxy_status, status.proxy_url or "No proxy")

    console.print(table)

    if not status.hf_reachable:
        console.print("\n[bold yellow]Suggestions:[/bold yellow]")
        if not status.hf_ssl_ok:
            console.print("  Try: [bold]hf2ollama pull --ssl-fix <repo>[/bold]")
