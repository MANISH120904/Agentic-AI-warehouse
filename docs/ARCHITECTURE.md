# Architecture

## Overview

WarehouseVoiceAI is a modular Python monolith:

- **FastAPI** — REST API for orders, inventory, delay risk, calls, feedback
- **JSON files** — simulated warehouse persistence
- **Streamlit** — operator dashboard (calls FastAPI only)
- **Edesy Hosted Voice Agent API** — real/mock outbound telephony
- **Google ADK** — separate browser voice agent with the same tools

```text
Phone --> Edesy voice agent --> HTTP tools --> FastAPI --> SQLite
ADK browser (Gemini Live) ------------------> FastAPI --> SQLite
Streamlit dashboard ------------------------> FastAPI --> SQLite
```

## Package layout

| Path | Role |
|---|---|
| `app/main.py` | FastAPI app |
| `app/config.py` | Typed settings |
| `app/api/` | HTTP routers |
| `app/services/` | Business logic |
| `app/agent/` | ADK `root_agent` + tools |
| `app/repositories/` | JSON persistence |
| `app/data/` | Sample datasets |
| `dashboard/app.py` | Streamlit UI |
| `scripts/register_edesy_functions.py` | Optional HTTP tool registration |
| `tests/` | Pytest suite (no live calls) |

## Data flow: outbound call

1. Operator confirms call in Streamlit.
2. Dashboard `POST /api/calls/outbound` with `confirm=true` + idempotency key.
3. If `MOCK_MODE` or incomplete Edesy config → write simulated call record.
4. Else `EdesyService.create_call` → `POST /api/v1/calls`.
5. Local `calls.json` stores provider `conversationId` / status.
6. Optional callback hits `/api/calls/callback`; app re-fetches provider truth.

## Security boundaries

- API keys stay in server `.env` only.
- Streamlit Settings page shows masked values.
- Provider errors are sanitized (no key material in logs/responses).
