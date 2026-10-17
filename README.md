# WarehouseVoiceAI

Hackathon MVP: an AI voice + operator stack for warehouse and delivery support.

- **Local SQLite database** (`app/data/warehouse.db`) seeded from JSON samples
- **FastAPI** backend reading/writing that local DB
- **Streamlit** operator dashboard (includes **Local Voice** instructions)
- **Google ADK** browser voice agent — talks with mic/speaker and calls tools against the **same local DB**
- **Edesy** outbound phone calls (optional; separate from local voice)

> **Local-first:** speak via ADK in the browser; tools query local SQLite. Phone (Edesy) is optional and does not share the ADK audio session.

## Architecture

```mermaid
flowchart LR
  Dash[Streamlit] --> API[FastAPI]
  ADK[ADK browser voice] --> Tools[Warehouse tools]
  API --> Tools
  Tools --> DB[(Local SQLite warehouse.db)]
  API --> Edesy[Edesy hosted Voice Agent API optional]
```

## Features

| Feature | Status |
|---|---|
| Local SQLite warehouse DB | Working (seeded from `app/data/*.json`) |
| Order / inventory / history lookup | Working against local DB |
| Delay risk heuristic | Working (simulated, labeled) |
| Feedback persistence | Working (local DB) |
| ADK browser voice + local DB tools | Working when `GOOGLE_API_KEY` set |
| Mock outbound calls | Working without telephony credits |
| Real outbound via Edesy | Optional when key, agent id, credits configured |
| Hosted Edesy HTTP tools → FastAPI | Needs public HTTPS URL |
| ADK audio on the phone call | **Not implemented** |
| Inbound customer dial-in | Needs Edesy number assignment — not local-default |

## Prerequisites

- Python 3.11+ (3.12 tested)
- Edesy account + API key (for live calls)
- Google AI Studio API key (for ADK browser voice)
- Mic/speakers for ADK demo

## Windows PowerShell setup

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env — never commit it. Rotate any key that was pasted into chat.
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

SIP fields (`EDESY_ACCOUNT_SID`, `EDESY_APPLICATION_SID`) belong to a different Edesy product and are unused here.

## Run the backend

```powershell
.\.venv\Scripts\Activate.ps1
$env:MOCK_MODE = "true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Health check: [http://127.0.0.1:8765/health](http://127.0.0.1:8765/health)

## Run the dashboard

```powershell
.\.venv\Scripts\Activate.ps1
$env:WAREHOUSE_API_BASE = "http://127.0.0.1:8765"
streamlit run dashboard/app.py --server.port 8510
```

Open the Streamlit URL shown in the terminal.

## Talk to local data (ADK voice)

This is the supported **local** voice path: microphone → Gemini Live → Python tools → **local SQLite**.

```powershell
.\.venv\Scripts\Activate.ps1
$env:GOOGLE_GENAI_USE_ENTERPRISE = "FALSE"
# Put GOOGLE_API_KEY in .env
$env:SSL_CERT_FILE = (python -m certifi)
cd app
adk web --port 8035
```

Select `agent` (`warehouse_voice_agent`), reload, click the mic. Try:

- “What is the status of order ORD-1001?”
- “How much stock is left for SKU-B210?”
- “What is the delay risk for ORD-1003?”

Dashboard → **Local Voice** also shows DB path/counts and the same tool lookups.

This browser voice session does **not** place a PSTN phone call.

## Edesy account & outbound setup

1. Rotate leaked keys; create a new API key with call/agent scopes.
2. Create an agent in Edesy (prompt + Live LLM provider).
3. Put `EDESY_API_KEY` and `EDESY_AGENT_ID` in `.env`.
4. Confirm wallet credits.
5. Set `MOCK_MODE=false`.
6. Use **Make a Call** in the dashboard with confirmation enabled.

Optional — let the hosted phone agent call your tools:

```powershell
$env:PUBLIC_BASE_URL = "https://your-public-https-url"
python scripts/register_edesy_functions.py --yes
```

## Inbound calls

Inbound only works if an Edesy phone number is assigned to your agent in the Edesy workspace. This repo does not auto-provision numbers. Verify in the Edesy dashboard before demoing inbound.

## Testing

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

Tests use mocked HTTP for Edesy and never place real calls.

## Mock mode

With `MOCK_MODE=true` (default):

- Dashboard, orders, inventory, delay risk, feedback work offline
- Outbound calls write simulated records labeled `is_mock`
- No telephony credits are consumed

## Known limitations

- ADK browser agent ≠ phone audio session
- Delay risk is a transparent heuristic, not ML
- Sample data is simulated
- Edesy call-ended callbacks are unsigned; app re-fetches provider state
- JSON files are for hackathon demos, not multi-writer production scale

## Security & privacy

- Never commit `.env`
- Never expose API keys to Streamlit or browser clients
- Rotate keys if they appeared in chat, screenshots, or logs
- Do not put real customer PII into the sample JSON for public demos

## Cost considerations

- Edesy outbound minutes / credits are billable
- Gemini Live / ADK usage is billable on your Google project
- Prefer `MOCK_MODE` while building UI and tests

## Docs

- [docs/INTEGRATION_NOTES.md](docs/INTEGRATION_NOTES.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Manual checklist (you)

1. Rotate Edesy + Gemini keys that were shared in chat
2. Verify Edesy credits, agent id, and a dashboard Test Call
3. Confirm Google Live model access for ADK
4. Only then set `MOCK_MODE=false` for a live dial
