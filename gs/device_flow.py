"""
Genspark Device Code & CLI Auth Module.
Allows automated polling and retrieval of gsk- API keys.
"""
import asyncio
import json
import time
import urllib.request
from typing import Optional, Tuple
from .config import BASE_URL

def request_device_code() -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}/api/cli_auth/device_code",
        data=b"{}",
        headers={"Content-Type": "application/json", "User-Agent": "gsk-cli/1.15.3"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def poll_device_token(device_code: str) -> dict:
    url = f"{BASE_URL}/api/cli_auth/token?code={urllib.parse.quote(device_code)}"
    req = urllib.request.Request(url, headers={"User-Agent": "gsk-cli/1.15.3"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

async def wait_for_approval(device_code: str, timeout: int = 300, interval: int = 5) -> Optional[str]:
    start = time.time()
    while time.time() - start < timeout:
        await asyncio.sleep(interval)
        try:
            res = poll_device_token(device_code)
            if res.get("status") == "approved" and res.get("api_key"):
                return res["api_key"]
            if res.get("status") == "expired":
                return None
        except Exception:
            pass
    return None
