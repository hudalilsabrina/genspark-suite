"""
Genspark Web-to-OpenAI Relay Server.
Relays OpenAI /v1/chat/completions directly to Genspark AI Chat endpoint (/api/agent/ask_proxy)
using harvested Genspark B2C accounts (with Claude Sonnet 4.6, Claude Opus 4.7, GPT-5, Grok, etc.)
Exposes port 20130 as an OpenAI-compatible upstream for 9Router!
"""
import asyncio
import json
import os
import random
import re
import time
from typing import List, Dict, Any
from aiohttp import web
from genspark import GensparkClient, stream_text

ACCOUNTS_FILE = "/root/genspark-suite/accounts.jsonl"
RELAY_PORT = 20130

def load_accounts() -> List[Dict[str, str]]:
    accs = []
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("email") and d.get("password"):
                        accs.append(d)
                except Exception:
                    pass
    return accs

# Client pool cache
CLIENT_POOL = {}

def get_client_for_account(acc: Dict[str, str]) -> GensparkClient:
    email = acc["email"]
    if email not in CLIENT_POOL:
        cookie_path = f"/root/genspark-suite/cookies_{email.split('@')[0]}.txt"
        client = GensparkClient(cookie_file=cookie_path)
        if not client.is_logged_in():
            client.login(email, acc["password"])
        CLIENT_POOL[email] = client
    return CLIENT_POOL[email]

async def handle_models(request):
    models = [
        {"id": "claude-sonnet-4-6", "object": "model", "owned_by": "genspark"},
        {"id": "claude-opus-4-7", "object": "model", "owned_by": "genspark"},
        {"id": "claude-haiku-4-5", "object": "model", "owned_by": "genspark"},
        {"id": "gpt-5.4", "object": "model", "owned_by": "genspark"},
        {"id": "gpt-5.2", "object": "model", "owned_by": "genspark"},
        {"id": "gemini-3.8-flash", "object": "model", "owned_by": "genspark"},
        {"id": "deep-seek-v4.1-flash", "object": "model", "owned_by": "genspark"},
        {"id": "grok-4.7", "object": "model", "owned_by": "genspark"}
    ]
    return web.json_response({"object": "list", "data": models})

async def handle_chat_completions(request):
    accs = load_accounts()
    if not accs:
        return web.json_response({"error": {"message": "No active Genspark accounts in suite"}}, status=503)

    body = await request.json()
    model = body.get("model", "claude-sonnet-4-6")
    # Strip prefix if any
    if "/" in model:
        model = model.split("/")[-1]

    messages = body.get("messages", [])
    # Extract last user message
    user_prompt = "Hello"
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                user_prompt = " ".join([c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")])
            else:
                user_prompt = str(content)
            break

    # Pick an account
    acc = random.choice(accs)
    
    def _do_chat():
        c = get_client_for_account(acc)
        resp = c.chat(user_prompt, model=model)
        full_text = []
        for chunk in stream_text(resp):
            full_text.append(chunk)
        return "".join(full_text)

    try:
        reply_text = await asyncio.to_thread(_do_chat)
    except Exception as e:
        return web.json_response({"error": {"message": str(e)}}, status=500)

    resp_data = {
        "id": f"chatcmpl-genspark-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": reply_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_prompt) // 4,
            "completion_tokens": len(reply_text) // 4,
            "total_tokens": (len(user_prompt) + len(reply_text)) // 4
        }
    }
    return web.json_response(resp_data)

def create_app():
    app = web.Application()
    app.router.add_get("/v1/models", handle_models)
    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=RELAY_PORT)
