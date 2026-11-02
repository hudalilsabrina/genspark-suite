"""
Genspark Storage module.
"""
import json
import os
import time

SUITE_DIR = "/root/genspark-suite"
ACCOUNTS_FILE = os.path.join(SUITE_DIR, "accounts.jsonl")
KEYS_FILE = os.path.join(SUITE_DIR, "keys.txt")

def save_account(email: str, api_key: str, password: str = "", extra: dict = None):
    os.makedirs(SUITE_DIR, exist_ok=True)
    record = {
        "email": email,
        "api_key": api_key,
        "password": password,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "extra": extra or {}
    }
    with open(ACCOUNTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    with open(KEYS_FILE, "a") as f:
        f.write(f"{api_key}\n")
