"""
Genspark Suite CLI Entrypoint.
"""
import argparse
import asyncio
import json
import sys
from .config import BASE_URL, LLM_PROXY_BASE
from .device_flow import request_device_code, wait_for_approval
from .sync_9router import sync_key_to_9router
from .store import save_account
from .http_worker import register_account_http
from .proxies import ProxyPool, to_playwright

def test_key(key: str, model: str = "gpt-4.1-mini"):
    import urllib.request
    req = urllib.request.Request(
        f"{LLM_PROXY_BASE}/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 10
        }).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Agent-Type": "hermesoffice"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"[TEST 200 OK] {r.read().decode()}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[TEST ERROR {e.code}] {e.read().decode()}")
        return False

async def main():
    p = argparse.ArgumentParser(description="Genspark Farm & LLM Proxy Suite")
    sub = p.add_subparsers(dest="cmd")

    dev_p = sub.add_parser("device-login", help="Generate CLI device login URL & poll for gsk- key")
    dev_p.add_argument("--timeout", type=int, default=300)

    test_p = sub.add_parser("test", help="Test an existing gsk- API key against LLM proxy")
    test_p.add_argument("key", help="API Key (gsk-...)")
    test_p.add_argument("--model", default="gpt-4.1-mini", help="Model ID")

    sync_p = sub.add_parser("sync", help="Sync an API key into 9Router")
    sync_p.add_argument("key", help="API Key (gsk-...)")

    farm_p = sub.add_parser("farm", help="Automated batch registration & key minting")
    farm_p.add_argument("-n", "--count", type=int, default=1, help="Jumlah akun yang ingin dipanen")
    farm_p.add_argument("-d", "--domain", default=None, help="Spesifikasikan domain (default: random rotate dari semua 350+ domain Tempik)")
    farm_p.add_argument("--proxy", action="store_true", help="Gunakan proxy pool rotating 9Router")
    farm_p.add_argument("--browser", action="store_true", help="Gunakan browser Camoufox (default: Pure HTTP super ringan)")

    args = p.parse_args()

    if args.cmd == "device-login":
        print("[*] Requesting Genspark Device Code...")
        dev = request_device_code()
        dcode = dev["device_code"]
        aurl = dev["auth_url"]
        print(f"[+] Device Code: {dcode}")
        print(f"[+] Silakan buka & approve di browser:")
        print(f"    {aurl}")
        print(f"[*] Menunggu persetujuan (timeout {args.timeout}s)...")
        key = await wait_for_approval(dcode, timeout=args.timeout)
        if key:
            print(f"\n🎉 BERHASIL MENDAPATKAN API KEY: {key}")
            save_account("device-flow-user", key)
            sync_key_to_9router(key)
            print("[+] Key tersimpan dan disinkronkan ke 9Router!")
        else:
            print("\n[-] Timeout atau otorisasi kedaluwarsa.")

    elif args.cmd == "test":
        print(f"[*] Testing key against {LLM_PROXY_BASE}...")
        test_key(args.key, args.model)

    elif args.cmd == "sync":
        ok = sync_key_to_9router(args.key)
        print(f"[*] Sync 9Router: {'Berhasil' if ok else 'Gagal'}")

    elif args.cmd == "farm":
        mode_str = "Browser Camoufox" if args.browser else "Pure HTTP (Super Cepat)"
        print(f"[*] Memulai batch harvesting ({args.count} akun) - Mode: {mode_str}...")
        pool = ProxyPool.from_9router() if args.proxy else None
        success_count = 0
        for i in range(args.count):
            print(f"\n[Batch Worker {i+1}/{args.count}]")
            p_url = None
            if pool:
                p_url = await pool.acquire()
            try:
                if args.browser:
                    from .worker import register_single_account
                    pw_proxy = to_playwright(p_url) if p_url else None
                    acc = await register_single_account(proxy=pw_proxy, domain=args.domain)
                else:
                    acc = await register_account_http(proxy_url=p_url, domain=args.domain)
                if acc:
                    success_count += 1
            except Exception as e:
                print(f"  [!] Worker exception: {e}")
            await asyncio.sleep(2)
        print(f"\n[+] Batch selesai! Berhasil: {success_count}/{args.count} akun.")

    else:
        p.print_help()

if __name__ == "__main__":
    asyncio.run(main())
