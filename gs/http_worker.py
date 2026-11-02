"""
Ultra-Fast Pure HTTP Automated Registration Worker for Genspark.
NO Browser / NO Camoufox required!
100% curl_cffi lightweight requests + Vision CAPTCHA solving.
"""
import asyncio
import base64
import json
import random
import re
import string
import time
from typing import Optional
from curl_cffi import requests as cr
from .captcha_solver import solve_captcha_image
from .tempik import create_inbox, wait_for_otp
from .store import save_account
from .sync_9router import sync_key_to_9router

LOGIN_INIT_URL = "https://www.genspark.ai/api/login?redirect_url=https://www.genspark.ai/"

def random_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "Genspark" + "".join(random.choices(chars, k=8)) + "1!"

async def register_account_http(proxy_url: Optional[str] = None, domain: Optional[str] = None) -> Optional[dict]:
    email = await create_inbox("gen", target_domain=domain)
    password = random_password()
    print(f"\n[*] [Pure HTTP] Starting auto-registration for: {email}")

    s = cr.Session(impersonate="chrome131")
    if proxy_url:
        s.proxies = {"http": proxy_url, "https": proxy_url}

    try:
        # 1. Init B2C OAuth
        r1 = s.get(LOGIN_INIT_URL, allow_redirects=True, timeout=20)
        csrf = s.cookies.get("x-ms-cpim-csrf")
        m_tx = re.search(r'"transId"\s*:\s*"([^"]+)"', r1.text)
        if not (csrf and m_tx):
            print("  [-] Gagal inisiasi B2C session.")
            return None
        tx = m_tx.group(1)

        # 2. Open Signup page state
        r2 = s.get(
            "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/api/CombinedSigninAndSignup/unified",
            params={"local": "signup", "csrf_token": csrf, "tx": tx, "p": "B2C_1_new_login"},
            headers={"Referer": r1.url},
            timeout=20
        )
        m_sett = re.search(r'SETTINGS\s*=\s*(\{[\s\S]*?\});', r2.text)
        if not m_sett:
            print("  [-] Gagal parse SETTINGS B2C.")
            return None
        sett = json.loads(m_sett.group(1))
        new_csrf = sett['csrf']
        new_tx = sett['transId']

        # 3. Request Captcha & Solve with VerifyChallenge validation
        print("  -> Mengambil & memecahkan B2C Visual Captcha...")
        solved_captcha = None
        cid = None
        region = "SouthCentralUS"

        for attempt in range(6):
            r_cap = s.get(
                "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/SelfAsserted/DisplayControlAction/vbeta/captchaControlChallengeCode/GetChallenge",
                params={"tx": new_tx, "p": "B2C_1_new_login", "challengeType": "Visual", "_": int(time.time()*1000)},
                headers={"x-csrf-token": new_csrf, "x-requested-with": "XMLHttpRequest", "Referer": r2.url},
                timeout=15
            )
            cap_data = r_cap.json()
            cid = cap_data.get('challengeId')
            region = cap_data.get('azureregion', 'SouthCentralUS')
            c_str = cap_data.get('challengeString', '')
            if "base64," in c_str:
                raw_img = base64.b64decode(c_str.split("base64,")[1])
                candidate = solve_captcha_image(raw_img)
                print(f"     [Attempt {attempt+1}] Solver output: {candidate}")
                if candidate and 4 <= len(candidate) <= 8:
                    # Validate against VerifyChallenge API
                    r_vcap = s.post(
                        "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/SelfAsserted/DisplayControlAction/vbeta/captchaControlChallengeCode/VerifyChallenge",
                        params={"tx": new_tx, "p": "B2C_1_new_login"},
                        headers={"x-csrf-token": new_csrf, "x-requested-with": "XMLHttpRequest", "Referer": r2.url},
                        data={"challengeId": cid, "captchaEntered": candidate, "challengeType": "Visual", "azureRegion": region},
                        timeout=15
                    )
                    if r_vcap.json().get('isCaptchaSolved', '').lower() == 'true':
                        print("     [+] Captcha valid & lolos verifikasi!")
                        solved_captcha = candidate
                        break
            await asyncio.sleep(1)

        if not solved_captcha:
            print("  [-] Gagal memecahkan captcha.")
            return None

        # 4. Send Email OTP
        print("  -> Mengirim OTP ke email Tempik...")
        r_send = s.post(
            "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/SelfAsserted/DisplayControlAction/vbeta/emailVerificationControl/SendCode",
            params={"tx": new_tx, "p": "B2C_1_new_login"},
            headers={"x-csrf-token": new_csrf, "x-requested-with": "XMLHttpRequest", "Referer": r2.url},
            data={"challengeId": cid, "captchaEntered": solved_captcha, "challengeType": "Visual", "azureRegion": region, "email": email},
            timeout=20
        )
        if r_send.status_code != 200 or r_send.json().get('status') != '200':
            print(f"  [-] SendCode ditolak: {r_send.text[:100]}")
            return None

        # 5. Wait OTP from Tempik
        print(f"  -> Menunggu OTP email di Tempik ({email})...")
        otp = await wait_for_otp(email, timeout=60)
        if not otp:
            print("  [-] Timeout menunggu OTP email.")
            return None
        print(f"  [+] OTP diterima: {otp}")

        # 6. Verify Code
        r_verify = s.post(
            "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/SelfAsserted/DisplayControlAction/vbeta/emailVerificationControl/VerifyCode",
            params={"tx": new_tx, "p": "B2C_1_new_login"},
            headers={"x-csrf-token": new_csrf, "x-requested-with": "XMLHttpRequest", "Referer": r2.url},
            data={"email": email, "emailVerificationCode": otp},
            timeout=20
        )
        if r_verify.json().get('status') != '200':
            print(f"  [-] Verifikasi kode gagal: {r_verify.text}")
            return None

        # 8. Submit Registration
        print("  -> Submit registrasi akun...")
        post_payload = {
            "email": email,
            "emailVerificationCode": otp,
            "captchaControlChallengeCode": solved_captcha,
            "newPassword": password,
            "reenterPassword": password,
            "emailPrivacy": "0",
            "request_type": "RESPONSE"
        }
        r_sub = s.post(
            "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/SelfAsserted",
            params={"tx": new_tx, "p": "B2C_1_new_login"},
            headers={
                "x-csrf-token": new_csrf,
                "x-requested-with": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": r2.url
            },
            data=post_payload,
            timeout=25
        )
        if r_sub.json().get('status') != '200':
            print(f"  [-] Submit registrasi gagal: {r_sub.text}")
            return None

        # 9. Finalize confirmed redirect to get genspark session_id
        r_conf = s.get(
            "https://login.genspark.ai/gensparkad.onmicrosoft.com/B2C_1_new_login/api/CombinedSigninAndSignup/confirmed",
            params={"rememberMe": "false", "csrf_token": new_csrf, "tx": new_tx, "p": "B2C_1_new_login"},
            headers={"Referer": r2.url},
            allow_redirects=True,
            timeout=25
        )

        sid = s.cookies.get("session_id")
        if not sid:
            print("  [-] Gagal mendapatkan session_id.")
            return None

        print(f"  🎉 REGISTRASI SUKSES (PURE HTTP)! Session ID: {sid[:25]}...")
        save_account(email, sid, password, extra={"session_id": sid})
        print("  [+] Akun otomatis ditambahkan ke Pool Web Relay 9Router!")

        return {
            "email": email,
            "password": password,
            "session_id": sid
        }

    except Exception as e:
        print(f"  [!] HTTP Worker error: {e}")
        return None
