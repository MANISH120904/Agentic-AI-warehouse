# WarehouseVoiceAI

Hackathon MVP: multimodal AI voice agent for warehouse and delivery support, with a local SQLite data plane, FastAPI tools, Streamlit ops dashboard, Google ADK browser voice, and optional Edesy telephony.

## Highlighted capabilities

| Capability | Status |
|---|---|
| **Multimodal implemented** | Voice (and ADK video-capable Live session) via Google ADK + Gemini Live; phone voice via Edesy hosted agent; operator UI in Streamlit |
| **Feedback loop implemented** | Ratings/comments persisted locally, linked to call IDs when present; dashboard satisfaction metric |
| **Self-healing feedback** | Safe idempotent reads retry once; outbound calls never auto-retry; provider/auth/balance errors surfaced; callbacks reconciled by re-fetching call state; sanitized error recording |
| **Execution time low** | In-process latency tracker on every HTTP request (`X-Execution-Time-Ms` + `GET /api/metrics/execution`, 500ms target) |

## Architecture

```text
                    +------------------+
  Phone ----------> | Edesy voice agent| ---HTTP tools---+
                    +------------------+                  |
                                                          v
  ADK browser ----> +---------------------------------------------+
  (Gemini Live)     |              FastAPI (local)                |
                    |  tools | feedback loop | self-healing       |
                    |  low-latency metrics                        |
                    +----------------------+----------------------+
                                           |
  Streamlit dashboard ---------------------|
                                           v
                                 +------------------+
                                 | SQLite warehouse |
                                 | (local .db file) |
                                 +------------------+
```

**Data plane is local:** FastAPI, ADK tools, and the dashboard all read/write `app/data/warehouse.db` (seeded from `app/data/*.json`).

## Features

| Feature | Status |
|---|---|
| Multimodal voice (ADK browser + Edesy phone) | Implemented |
| Feedback loop + satisfaction metric | Implemented |
| Self-healing reads / bounded recovery | Implemented |
| Low execution-time tracking | Implemented (`/api/metrics/execution`) |
| Local SQLite warehouse DB | Working |
| Order / inventory / history / delay risk | Working |
| Mock outbound calls | Working without credits |
| Real Edesy outbound | When key, agent id, credits configured |
| Hosted Edesy HTTP tools → FastAPI | Needs public HTTPS tunnel |
| Inbound dial-in | Needs own Edesy number (shared trial is outbound-only) |

## Prerequisites

- Python 3.11+ (3.12 tested)
- Edesy/Vani account (for live phone)
- Google AI Studio API key (for ADK browser voice)
- Mic/speakers for ADK demo

## Windows PowerShell setup

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env — never commit secrets
```

### Environment

See `.env.example`. Important variables:

| Variable | Purpose |
|---|---|
| `WAREHOUSE_DB_PATH` | Local SQLite file (default `app/data/warehouse.db`) |
| `MOCK_MODE` | `true` simulates outbound phone calls (default) |
| `EDESY_API_KEY` | Hosted Voice Agent API key (`vp_live_…`) |
| `EDESY_API_BASE_URL` | Default `https://voice-agent.edesy.in/api/v1` |
| `EDESY_AGENT_ID` | Numeric agent id from Edesy |
| `EDESY_FROM_NUMBER` | Optional caller ID |
| `PUBLIC_BASE_URL` | Public HTTPS base for Edesy HTTP tools / callbacks |
| `GOOGLE_API_KEY` | ADK / Gemini |
| `ADK_MODEL` | Live-capable Gemini model id |

## Run the backend

```powershell
.\.venv\Scripts\Activate.ps1
$env:MOCK_MODE = "true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

- Health: http://127.0.0.1:8765/health  
- Latency: http://127.0.0.1:8765/api/metrics/execution  

## Run the dashboard

```powershell
.\.venv\Scripts\Activate.ps1
$env:WAREHOUSE_API_BASE = "http://127.0.0.1:8765"
streamlit run dashboard/app.py --server.port 8510
```

## Talk to local data (ADK multimodal voice)

```powershell
.\.venv\Scripts\Activate.ps1
$env:GOOGLE_GENAI_USE_ENTERPRISE = "FALSE"
$env:SSL_CERT_FILE = (python -m certifi)
cd app
adk web --port 8035
```

Select `warehouse_voice_agent`, use mic (and camera if testing video Live). Ask about `ORD-1001` / `SKU-B210`.

## Edesy phone setup (optional)

1. Create agent + custom HTTP functions → your public FastAPI `/api/tools/*`
2. Credits required
3. Shared trial DID is often **outbound only** — buy your own number for inbound
4. Outbound/Test Call dials **your** mobile; inbound = you dial the workspace number

```powershell
$env:PUBLIC_BASE_URL = "https://your-public-https-url"
python scripts/register_edesy_functions.py --yes
```

## Testing

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

## Mock mode

`MOCK_MODE=true` (default): full warehouse + mock calls, no telephony spend.

## Known limitations

- ADK browser session ≠ PSTN audio session
- Delay risk is heuristic / simulated
- Shared Edesy trial numbers may block inbound
- Hackathon SQLite — not multi-region production scale

## Security & privacy

- Never commit `.env`
- Never expose API keys to the browser
- Rotate keys if pasted into chat

## Docs

- [docs/INTEGRATION_NOTES.md](docs/INTEGRATION_NOTES.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
