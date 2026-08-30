"""SSL certificate configuration - use OS trust store instead of certifi defaults."""

from __future__ import annotations

import logging
import os
import ssl
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)
_PATCHED = False


def apply_ssl_fix(
    ca_bundle: str | None = None,
    proxy: str | None = None,
) -> str:
    """Configure Python to use the OS certificate store for SSL verification.

    Exports system CA certificates and sets environment variables so that
    httpx, requests, and urllib3 use the OS trust store.

    Returns the path to the CA bundle being used.
    """
    global _PATCHED
    if _PATCHED:
        return os.environ.get("SSL_CERT_FILE", "")

    bundle = ca_bundle or _export_system_certs()
    os.environ["SSL_CERT_FILE"] = bundle
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["CURL_CA_BUNDLE"] = bundle

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy

    _PATCHED = True
    return bundle


def _export_system_certs() -> str:
    """Export system certificates to a PEM file."""
    certs: set[str] = set()

    ctx = ssl.create_default_context()
    for cert_der in ctx.get_ca_certs(binary_form=True):
        pem = ssl.DER_cert_to_PEM_cert(cert_der)
        certs.add(pem)

    try:
        import certifi

        with open(certifi.where(), "r", encoding="utf-8") as f:
            content = f.read()
        in_cert = False
        current: list[str] = []
        for line in content.splitlines(True):
            if "BEGIN CERTIFICATE" in line:
                in_cert = True
                current = [line]
            elif "END CERTIFICATE" in line:
                current.append(line)
                certs.add("".join(current))
                in_cert = False
            elif in_cert:
                current.append(line)
    except ImportError:
        pass

    cert_dir = Path(tempfile.gettempdir()) / "hf2ollama"
    cert_dir.mkdir(exist_ok=True)
    bundle = cert_dir / "ca_bundle.pem"
    bundle.write_text("\n".join(sorted(certs)), encoding="utf-8")
    return str(bundle)
