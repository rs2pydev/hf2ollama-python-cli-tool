"""Network environment detection - SSL and HuggingFace reachability checks."""

from __future__ import annotations

import logging
import os
import ssl
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NetworkStatus:
    """Result of a network diagnostic check."""

    hf_reachable: bool = False
    hf_ssl_ok: bool = False
    hf_error: str = ""
    proxy_configured: bool = False
    proxy_url: str = ""
    system_certs_available: bool = False
    cert_count: int = 0


def check_network() -> NetworkStatus:
    """Check HuggingFace reachability and SSL certificate status."""
    status = NetworkStatus()

    status.proxy_url = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", ""))
    status.proxy_configured = bool(status.proxy_url)

    try:
        ctx = ssl.create_default_context()
        certs = ctx.get_ca_certs(binary_form=True)
        status.cert_count = len(certs)
        status.system_certs_available = status.cert_count > 50
    except (ssl.SSLError, OSError) as e:
        logger.debug("Failed to read system certs: %s", e)

    try:
        httpx.get("https://huggingface.co/api/models?limit=1", timeout=10.0)
        status.hf_reachable = True
        status.hf_ssl_ok = True
    except httpx.ConnectError as e:
        err = str(e).lower()
        if "ssl" in err or "certificate" in err:
            status.hf_reachable = False
            status.hf_ssl_ok = False
            status.hf_error = "SSL certificate verification failed"
        else:
            status.hf_error = str(e)[:100]
    except (httpx.TimeoutException, httpx.HTTPStatusError, OSError) as e:
        status.hf_error = str(e)[:100]

    return status
