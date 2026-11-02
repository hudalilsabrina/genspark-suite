# Genspark Suite (Pure HTTP Fast Harvester & Web Relay)

Automated account harvesting, Microsoft Azure AD B2C Visual CAPTCHA auto-solving, and OpenAI-compatible Web Relay server for Genspark (`genspark.ai`).

Relays requests across all frontier models:
- **Claude**: `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5`
- **GPT**: `gpt-5.4`, `gpt-5.2`
- **Google**: `gemini-3.8-flash`
- **DeepSeek & Others**: `deep-seek-v4.1-flash`, `grok-4.7`

---

## Features

- **Pure HTTP Mode**: Extremely lightweight (no browser required for farming). Solves registration in ~12 seconds.
- **Vision CAPTCHA Solving**: Solves Azure AD B2C hollow multi-tier outline fonts automatically via Vision model / OCR.
- **Mail Support**:
  - Defaults to public `tempmail.lol` API.
  - Optional support for self-hosted Tempik via environment variables.
- **OpenAI-Compatible Relay Server**: Bridges standard OpenAI `/v1/chat/completions` directly into Genspark web chat multi-account pool.
- **9Router Sync**: Automatically registers and maintains active accounts in 9Router.

---

## Quick Start

### 1. Installation
Clone the repository and run setup:
```bash
git clone https://github.com/hudalilsabrina/genspark-suite.git
cd genspark-suite
chmod +x setup.sh run.sh
./setup.sh
```

### 2. Harvest Accounts
```bash
# Harvest 5 accounts using Pure HTTP (Fast):
./run.sh farm -n 5

# Optional: Harvest using rotating proxy pool
./run.sh farm -n 10 --proxy

# Optional: Headless browser mode
./run.sh farm -n 1 --browser
```

### 3. Start OpenAI Relay Server
```bash
python3 -m gs.relay_server
```
The relay runs on `http://127.0.0.1:20130/v1` and accepts standard OpenAI chat completion payloads.

---

## Configuration (Environment Variables)

| Variable | Default | Description |
|---|---|---|
| `MAIL_PROVIDER` | `tempmail.lol` | Mail provider (`tempmail.lol` or `tempik`) |
| `TEMPIK_BASE` | `""` | Base URL for private Tempik service |
| `TEMPIK_DOMAIN` | `""` | Default domain for Tempik |
| `VISION_BASE_URL` | `http://127.0.0.1:20128/v1` | Endpoint for CAPTCHA Vision solver |
| `VISION_MODEL` | `ag/gemini-2.5-flash` | Model for Vision CAPTCHA solver |
| `NINEROUTER_DB` | `/var/lib/9router/db/data.sqlite` | SQLite database path for 9Router |

---

## License
MIT
