#!/usr/bin/env python3
"""CI entry point with compatibility for Adelaide's legacy TLS endpoint."""
from __future__ import annotations

import ssl
import urllib.request

import sync_external_knowledge as sync


def request_bytes(url: str, timeout: int = 180) -> bytes:
    context = ssl.create_default_context()
    # The Adelaide download endpoint still negotiates using legacy TLS
    # renegotiation. Limit this compatibility context to this sync client.
    legacy_flag = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
    context.options |= legacy_flag
    try:
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
    except ssl.SSLError:
        pass
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SommelierSimulatorKnowledgeSync/2.0 (+research dataset refresh)"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
        return response.read()


sync.request_bytes = request_bytes
sync.main()
