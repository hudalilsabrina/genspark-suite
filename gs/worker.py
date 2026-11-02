"""
Full Automated Registration Worker for Genspark.
- Creates Tempik email
- Solves Azure AD B2C Visual Captcha via 9Router Vision
- Sends & captures verification code from Tempik
- Sets password & submits form
- Extracts session / mints API key via CLI device flow
"""
import asyncio
import base64
import json
import random
import string
import time
from typing import Optional
from camoufox.async_api import AsyncCamoufox
from .captcha_solver import solve_captcha_image
from .tempik import create_inbox, wait_for_otp
from .device_flow import request_device_code, poll_device_token
from .store import save_account
from .sync_9router import sync_key_to_9router

LOGIN_URL = "https://www.genspark.ai/api/login?redirect_url=https://www.genspark.ai/"

def random_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "Genspark" + "".join(random.choices(chars, k=8)) + "1!"

async def register_single_account(proxy: Optional[dict] = None, domain: Optional[str] = None) -> Optional[dict]:
    email = await create_inbox("gensp", target_domain=domain)
    password = random_password()
    print(f"\n[*] Starting auto-registration for: {email}")

    kw = {
        "headless": True,
        "humanize": True,
        "os": "windows",
        "geoip": True,
        "locale": "en-US",
        "i_know_what_im_doing": True
    }
    if proxy:
        kw["proxy"] = proxy

    async with AsyncCamoufox(**kw) as b:
        p = await b.new_page()

        # 1. Navigate to B2C login
        print("  -> Loading Genspark B2C flow...")
        await p.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        
        # Cloudflare check
        for _ in range(25):
            cf = [f for f in p.frames if "challenges.cloudflare.com" in f.url]
            if cf:
                try:
                    box = await (await cf[0].frame_element()).bounding_box()
                    if box and box["width"] > 20:
                        await p.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        await asyncio.sleep(4)
        
        # 2. Click Sign up now
        print("  -> Opening Sign up form...")
        await p.wait_for_selector("#createAccount", timeout=15000)
        await p.click("#createAccount")
        await asyncio.sleep(4)

        # 3. Fill email
        await p.fill("#email", email)

        # 4. Extract and solve Captcha image
        print("  -> Capturing & solving B2C Visual Captcha...")
        solved_captcha = None
        for attempt in range(5):
            img_src = await p.evaluate("""() => {
                const img = document.querySelector('img[id*="captcha" i], img[src*="captcha" i]');
                return img ? img.src : null;
            }""")
            if img_src and "base64," in img_src:
                raw_bytes = base64.b64decode(img_src.split("base64,")[1])
                solved_captcha = solve_captcha_image(raw_bytes)
                print(f"     [Attempt {attempt+1}] Solver output: {solved_captcha}")
                # Microsoft B2C visual captcha is typically 4 to 6 uppercase chars
                if solved_captcha and 4 <= len(solved_captcha) <= 6:
                    break
            # If failed or too long/short, refresh captcha
            await p.evaluate("""() => {
                const btn = document.querySelector('#captchaControlChallengeCode-generateCaptchaBtn');
                if (btn) btn.click();
            }""")
            await asyncio.sleep(2)

        if not solved_captcha:
            print("  [-] Gagal menyelesaikan Captcha.")
            return None

        await p.fill("#captchaControlChallengeCode", solved_captcha)

        # 5. Click Send verification code
        print("  -> Submitting captcha and requesting email OTP...")
        await p.click("#emailVerificationControl_but_send_code")
        await asyncio.sleep(4)

        # Check if captcha failed / rejected
        has_error = await p.evaluate("""() => {
            const err = document.querySelector('#captchaControlChallengeCode-error, #claimVerificationServerError');
            return err && err.style.display !== 'none' && err.innerText.trim() ? err.innerText.trim() : null;
        }""")
        if has_error and any(w in has_error.lower() for w in ['didn', 'match', 'incorrect', 'invalid']):
            print(f"  [-] Captcha ditolak: {has_error}")
            return None

        # 6. Wait for OTP from Tempik
        print(f"  -> Menunggu OTP email di Tempik ({email})...")
        otp = await wait_for_otp(email, timeout=90)
        if not otp:
            print("  [-] Timeout menunggu OTP.")
            return None
        print(f"  [+] OTP diterima: {otp}")

        # 7. Fill verification code & verify
        print("  -> Verifikasi kode OTP...")
        await p.wait_for_selector("#emailVerificationCode", timeout=10000)
        await p.fill("#emailVerificationCode", otp)
        await p.click("#emailVerificationControl_but_verify_code")
        await asyncio.sleep(4)

        # 8. Set password and submit Create
        print("  -> Menyetel password akun & submit Create...")
        await p.fill("#newPassword", password)
        await p.fill("#reenterPassword", password)
        await p.click("#continue")
        await asyncio.sleep(8)

        # Check authenticated session
        session_id = None
        cookies = await p.context.cookies()
        for c in cookies:
            if c["name"] == "session_id":
                session_id = c["value"]
                break

        print(f"  [+] Registrasi tuntas! Session ID: {session_id[:20] if session_id else 'Found'}")

        # 9. Mint API Key via device flow inside this session
        print("  -> Minting API key via internal CLI device approval...")
        api_key = None
        try:
            dev = request_device_code()
            dcode = dev.get("device_code")
            aurl = dev.get("auth_url")
            
            if dcode and aurl:
                # Navigate to auth_url to approve
                await p.goto(aurl, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                # Click Approve / Continue button if present
                await p.evaluate("""() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => /approve|allow|continue|confirm/i.test(b.innerText));
                    if (btn) btn.click();
                }""")
                await asyncio.sleep(3)

                # Poll token
                for _ in range(8):
                    await asyncio.sleep(2)
                    t_resp = poll_device_token(dcode)
                    if t_resp.get("status") == "approved" and t_resp.get("api_key"):
                        api_key = t_resp["api_key"]
                        break
        except Exception as e:
            print(f"  [!] Device flow error: {e}")

        print(f"  🎉 API KEY DIPEROLEH: {api_key if api_key else 'Session-only'}")

        # Save record
        save_account(email, api_key or session_id or "session-active", password, extra={"session_id": session_id})
        if api_key:
            sync_key_to_9router(api_key, email)
            print("  [+] Kredensial tersinkron ke 9Router (genspark/*)!")
        else:
            print("  [+] Akun aktif tersimpan ke Pool Web Relay!")

        return {
            "email": email,
            "password": password,
            "api_key": api_key,
            "session_id": session_id
        }
