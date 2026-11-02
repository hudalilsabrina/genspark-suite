"""
9Router Sync Module for Genspark LLM Proxy.
Connects directly to providerNodes: GensparkAI
Node ID: openai-compatible-chat-3211c68f-0735-4e1e-bbc0-87254551979f
Prefix: gs/*
Base URL: https://www.genspark.ai/api/llm_proxy/v1
"""
import json
import sqlite3
import time
import uuid
from typing import Optional
from .config import NINEROUTER_DB

NODE_ID = "openai-compatible-chat-3211c68f-0735-4e1e-bbc0-87254551979f"
NODE_NAME = "GensparkAI"
PREFIX = "gs"
BASE_URL = "https://www.genspark.ai/api/llm_proxy/v1"

def sync_key_to_9router(api_key: str, account_email: str = "") -> bool:
    try:
        conn = sqlite3.connect(NINEROUTER_DB)
        cur = conn.cursor()
        
        # Check if this exact apiKey is already registered
        cur.execute("SELECT id, data FROM providerConnections WHERE provider = ?", (NODE_ID,))
        rows = cur.fetchall()
        for r_id, r_data in rows:
            try:
                d = json.loads(r_data)
                if d.get("apiKey") == api_key:
                    conn.close()
                    return True
            except Exception:
                pass

        conn_id = str(uuid.uuid4())
        name = account_email.split("@")[0] if account_email else f"gs-{conn_id[:6]}"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        
        data_payload = {
            "apiKey": api_key,
            "testStatus": "active",
            "providerSpecificData": {
                "prefix": PREFIX,
                "apiType": "chat",
                "baseUrl": BASE_URL,
                "nodeName": NODE_NAME,
                "quotaEnabled": False,
                "quotaPath": "/credits",
                "connectionProxyEnabled": False,
                "connectionProxyUrl": "",
                "connectionNoProxy": "",
                "customHeaders": {
                    "X-Agent-Type": "hermesoffice"
                }
            }
        }

        cur.execute(
            """INSERT INTO providerConnections 
               (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conn_id, NODE_ID, "apikey", name, account_email or None, 0, 1, json.dumps(data_payload), now_iso, now_iso)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[9Router Sync Error] {e}")
        return False
