"""
Genspark Suite Configuration & Constants.
"""
import os

BASE_URL = "https://www.genspark.ai"
LLM_PROXY_BASE = "https://www.genspark.ai/api/llm_proxy/v1"
ANTHROPIC_PROXY_BASE = "https://www.genspark.ai/api/anthropic/v1"
GEMINI_PROXY_BASE = "https://www.genspark.ai/api/llm_proxy/gemini/v1beta"

# Mail provider configuration (Default: tempmail.lol / Custom: tempik via env)
MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "tempmail.lol")
TEMPIK_BASE = os.environ.get("TEMPIK_BASE", "")
TEMPIK_DOMAIN = os.environ.get("TEMPIK_DOMAIN", "")

# Azure AD B2C URLs
B2C_LOGIN_URL = "https://login.genspark.ai"
B2C_TENANT = "gensparkad.onmicrosoft.com"
B2C_POLICY = "B2C_1_new_login"

# 9Router SQLite path
NINEROUTER_DB = os.environ.get("NINEROUTER_DB", "/var/lib/9router/db/data.sqlite")
