"""
Proxy Pool integration with 9Router.
"""
import json
import random
import sqlite3
from typing import Optional
from .config import NINEROUTER_DB

class ProxyPool:
    def __init__(self, proxies: list[str], sticky: Optional[str] = None):
        self.proxies = proxies
        self.sticky = sticky

    @classmethod
    def from_9router(cls, pool_name: Optional[str] = None, sticky: Optional[str] = None) -> "ProxyPool":
        try:
            conn = sqlite3.connect(NINEROUTER_DB)
            cur = conn.cursor()
            if pool_name:
                cur.execute("SELECT data FROM proxyPools WHERE name = ? LIMIT 1", (pool_name,))
            else:
                cur.execute("SELECT data FROM proxyPools LIMIT 1")
            row = cur.fetchone()
            conn.close()
            if row:
                d = json.loads(row[0])
                p_url = d.get("proxyUrl")
                if p_url:
                    return cls([p_url], sticky=sticky)
        except Exception:
            pass
        return cls([], sticky=sticky)

    async def acquire(self) -> Optional[str]:
        if not self.proxies:
            return None
        base = random.choice(self.proxies)
        if self.sticky:
            rnd = random.randint(100000, 999999)
            if "@" in base:
                proto, rest = base.split("://", 1)
                auth, host = rest.split("@", 1)
                user, pwd = auth.split(":", 1)
                return f"{proto}://{user}-{self.sticky}{rnd}:{pwd}@{host}"
        return base

def to_playwright(proxy_str: Optional[str]) -> Optional[dict]:
    if not proxy_str:
        return None
    proto, rest = proxy_str.split("://", 1)
    if "@" in rest:
        auth, host = rest.split("@", 1)
        user, pwd = auth.split(":", 1)
        return {"server": f"{proto}://{host}", "username": user, "password": pwd}
    return {"server": proxy_str}
