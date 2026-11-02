"""
Mail Client with Provider Abstraction (Tempmail.lol public default + Tempik private support).
"""
import asyncio
import json
import random
import re
import string
import urllib.request
from typing import Optional, List, Dict, Any
from .config import MAIL_PROVIDER, TEMPIK_BASE, TEMPIK_DOMAIN

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# Cache for Tempik available domains
_AVAILABLE_DOMAINS: List[str] = []

async def areq(url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> Any:
    def _do():
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", UA)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if data and "Content-Type" not in (headers or {}):
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    return await asyncio.to_thread(_do)

# =========================================================================
# 1. Tempmail.lol Provider (Public Default)
# =========================================================================
_LOL_TOKEN: Optional[str] = None

async def _lol_create_inbox() -> str:
    global _LOL_TOKEN
    res = await areq("https://api.tempmail.lol/v2/inbox/create")
    _LOL_TOKEN = res.get("token")
    return res.get("address")

async def _lol_wait_for_otp(email: str, timeout: int = 120, interval: float = 2.0) -> Optional[str]:
    global _LOL_TOKEN
    if not _LOL_TOKEN:
        return None
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        await asyncio.sleep(interval)
        try:
            res = await areq(f"https://api.tempmail.lol/v2/inbox?token={_LOL_TOKEN}")
            emails = res.get("emails", [])
            for em in emails:
                subject = em.get("subject", "")
                body = em.get("body", "") or em.get("html", "")
                full = f"{subject} {body}"
                codes = re.findall(r"\b(\d{6})\b", full)
                if codes:
                    return codes[0]
        except Exception:
            pass
    return None

# =========================================================================
# 2. Tempik Provider (Opt-in via env TEMPIK_BASE)
# =========================================================================
async def _tempik_get_domains() -> List[str]:
    global _AVAILABLE_DOMAINS
    base = TEMPIK_BASE.rstrip("/")
    if not _AVAILABLE_DOMAINS and base:
        try:
            cfg = await areq(f"{base}/config")
            doms = cfg.get("mailDomains", [])
            if doms:
                _AVAILABLE_DOMAINS = doms
        except Exception:
            pass
    return _AVAILABLE_DOMAINS

async def _tempik_create_inbox(prefix: str = "gen", target_domain: Optional[str] = None) -> str:
    base = TEMPIK_BASE.rstrip("/")
    doms = await _tempik_get_domains()
    domain = target_domain or (random.choice(doms) if doms else TEMPIK_DOMAIN or "example.com")
    sess = await areq(f"{base}/session")
    sid = sess.get("sessionId") or sess.get("id")
    local = prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    payload = json.dumps({"localPart": local, "domain": domain, "sessionId": sid}).encode()
    inbox = await areq(f"{base}/inboxes", payload)
    return inbox.get("address") or f"{local}@{domain}"

async def _tempik_wait_for_otp(email: str, timeout: int = 120, interval: float = 1.5) -> Optional[str]:
    base = TEMPIK_BASE.rstrip("/")
    start = asyncio.get_event_loop().time()
    seen = set()
    while asyncio.get_event_loop().time() - start < timeout:
        await asyncio.sleep(interval)
        try:
            res = await areq(f"{base}/inboxes/{email}/messages")
            msgs = res if isinstance(res, list) else (res.get("messages") or res.get("data") or [])
            for m in msgs:
                if m.get("code"):
                    return m["code"]
                mid = m.get("id")
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                det = await areq(f"{base}/inboxes/{email}/messages/{mid}")
                html = det.get("body_html") or det.get("body") or ""
                clean = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", clean)
                codes = re.findall(r"\b(\d{6})\b", text)
                if codes:
                    return codes[0]
        except Exception:
            pass
    return None

# =========================================================================
# Unified Dispatcher
# =========================================================================
async def create_inbox(prefix: str = "gen", target_domain: Optional[str] = None) -> str:
    if MAIL_PROVIDER.lower() == "tempik" and TEMPIK_BASE:
        return await _tempik_create_inbox(prefix, target_domain)
    # Default public
    return await _lol_create_inbox()

async def wait_for_otp(email: str, timeout: int = 120, interval: float = 2.0) -> Optional[str]:
    if MAIL_PROVIDER.lower() == "tempik" and TEMPIK_BASE:
        return await _tempik_wait_for_otp(email, timeout, interval)
    return await _lol_wait_for_otp(email, timeout, interval)
