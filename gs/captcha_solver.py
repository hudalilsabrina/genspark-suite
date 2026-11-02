"""
Genspark Azure AD B2C Visual Captcha Solver.
Solves the hollow multi-tier outline font using an OpenAI/Gemini Vision compatible endpoint or ddddocr fallback.
"""
import base64
import json
import os
import re
import sqlite3
import urllib.request
from typing import Optional
from .config import NINEROUTER_DB

VISION_BASE_URL = os.environ.get("VISION_BASE_URL", "http://127.0.0.1:20128/v1")
VISION_MODEL = os.environ.get("VISION_MODEL", "ag/gemini-2.5-flash")
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")

def _get_api_key() -> str:
    if VISION_API_KEY:
        return VISION_API_KEY
    if os.path.exists(NINEROUTER_DB):
        try:
            conn = sqlite3.connect(NINEROUTER_DB)
            row = conn.execute("SELECT key FROM apiKeys WHERE name = 'Default Keys' LIMIT 1").fetchone()
            if not row:
                row = conn.execute("SELECT key FROM apiKeys LIMIT 1").fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception:
            pass
    return "default"

def solve_captcha_image(img_bytes: bytes) -> Optional[str]:
    api_key = _get_api_key()
    try:
        b64_img = base64.b64encode(img_bytes).decode()
        req = urllib.request.Request(
            f"{VISION_BASE_URL.rstrip('/')}/chat/completions",
            data=json.dumps({
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What are the exact characters in this CAPTCHA image? Output ONLY the characters in uppercase, no spaces, no punctuation."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }
                ],
                "max_tokens": 10
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            chunks = []
            for line in raw.split('\n'):
                if line.startswith('data: '):
                    d_str = line[6:].strip()
                    if d_str == '[DONE]':
                        break
                    try:
                        d = json.loads(d_str)
                        c = d['choices'][0].get('delta', {}).get('content') or d['choices'][0].get('message', {}).get('content') or ''
                        chunks.append(c)
                    except Exception:
                        pass
                elif line.strip().startswith('{'):
                    try:
                        d = json.loads(line)
                        c = d['choices'][0]['message']['content']
                        chunks.append(c)
                    except Exception:
                        pass
            ans = "".join(chunks).strip()
            clean = re.sub(r'[^A-Z0-9]', '', ans.upper())
            return clean if clean else None
    except Exception as e:
        print(f"[Captcha Solver Error] {e}")
        # Local OCR fallback if available
        try:
            import ddddocr
            ocr = ddddocr.DdddOcr(show_ad=False)
            res = ocr.classification(img_bytes)
            clean = re.sub(r'[^A-Z0-9]', '', res.upper())
            if clean:
                return clean
        except Exception:
            pass
        return None
