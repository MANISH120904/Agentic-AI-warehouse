# Troubleshooting

## Backend will not start

- Activate the virtual environment.
- Install deps: `pip install -r requirements.txt`
- Run from repo root so `app` is importable:
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`

## Dashboard cannot reach API

- Confirm FastAPI is running on port `8765`.
- Override with `WAREHOUSE_API_BASE=http://127.0.0.1:8765` when launching Streamlit.

## Mock calls appear instead of real calls

Expected when:

- `MOCK_MODE=true`, or
- `EDESY_API_KEY` / `EDESY_AGENT_ID` missing

Set `MOCK_MODE=false` and configure Edesy for live dialing.

## Edesy authentication fails

- Rotate and paste a fresh key into `.env` (never commit it).
- Confirm key prefix `vp_live_` / `vp_test_`.
- Hit Settings → **Check Edesy connectivity** or `GET /api/edesy/status`.

## Insufficient credits (HTTP 402)

Top up the Edesy wallet. The app records a failed call and does not claim success.

## Duplicate calls

`POST /calls` is not idempotent on Edesy. This app:

- requires `confirm=true`
- stores `idempotency_key` locally
- never auto-retries outbound create after timeout

If a timeout occurs, check Call History / Edesy dashboard before placing again.

## Phone agent cannot look up orders

Hosted tools need a public HTTPS `PUBLIC_BASE_URL`. Localhost is not enough. Expose the API (tunnel/deploy), then run:

```powershell
python scripts/register_edesy_functions.py --yes
```

## ADK browser voice fails

- Set `GOOGLE_API_KEY` and `GOOGLE_GENAI_USE_ENTERPRISE=FALSE`
- Use a Live-capable `ADK_MODEL`
- Set `SSL_CERT_FILE` via `python -m certifi`
- Reload the browser before clicking the microphone
- Native-audio models may not support text chat in `adk web`

## ADK is not talking on the phone

By design in this MVP. Phone audio is handled by the hosted Edesy agent. ADK is a separate browser demo. See `docs/INTEGRATION_NOTES.md`.
