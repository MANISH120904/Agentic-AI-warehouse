# Integration Notes

## Chosen telephony product

**Edesy Hosted Voice Agent API**

| Item | Value |
|---|---|
| Base URL | `https://voice-agent.edesy.in/api/v1` |
| OpenAPI | `https://voice-agent.edesy.in/api/v1/openapi.json` |
| Auth | `Authorization: Bearer vp_live_…` or `X-API-Key: vp_live_…` |
| Key prefixes | `vp_live_` (prod), `vp_test_` (non-prod) |
| Primary docs | https://www.edesy.in/docs/voice-agent/api |

### Capabilities used in this MVP

- List/read agents (`GET /agents`)
- Place outbound call (`POST /calls`) with `agentId`, `phoneNumber`, optional `variables`, `metadata`, `callbackUrl`, `fromNumber`
- Call history / detail / transcript (`GET /calls`, `GET /calls/{id}`, `GET /calls/{id}/transcript`)
- Optional HTTP tools (`POST /functions`) pointing at FastAPI `/api/tools/*`

### Product explicitly not used for MVP

**Edesy SIP Trunk / Voice Platform** at `https://voice-api.edesy.in/v1`

That product requires Account SID, Application SID, owned `from` number, and a public WebSocket (`wss://`) that receives L16 PCM audio. It is the path for a custom ADK audio bridge. This MVP does **not** implement that bridge.

Do not mix the two base URLs or credential sets.

## Google ADK

- Browser voice agent via official `adk web` UI
- Uses Gemini Live-capable model from `ADK_MODEL`
- Tools call the same local Python services / JSON data
- **Not** connected to PSTN audio in this MVP

## Bridge options (truth table)

| Goal | Supported in MVP? | How |
|---|---|---|
| Dashboard mock calls | Yes | `MOCK_MODE=true` |
| Real outbound phone call | Yes, when configured + credits | Hosted `POST /calls` |
| Phone agent looks up warehouse data | Yes, with public HTTPS | Register HTTP functions → FastAPI |
| ADK browser voice + tools | Yes | `adk web` |
| ADK model hearing/speaking on the phone | No | Would need SIP WebSocket audio bridge |

## Manual account checks (operator)

1. Rotate any API key that was pasted into chat.
2. Confirm Edesy wallet/credits > 0.
3. Create or select an agent; note numeric `EDESY_AGENT_ID`.
4. Ensure the agent has prompt + LLM provider configured (docs example: `gemini-live-2.5`).
5. Place a Test Call from the Edesy dashboard before using this app.
6. For live tool calls from the phone agent: expose FastAPI via HTTPS (`PUBLIC_BASE_URL`) and run `python scripts/register_edesy_functions.py --yes`.
7. Confirm Google AI Studio key works with a Live model for `adk web`.

## Error codes handled

| Situation | Behavior |
|---|---|
| Missing/invalid key | Surface auth error; no call claimed |
| HTTP 402 / insufficient credits | Fail clearly; record failed local call |
| Timeout on `POST /calls` | Do **not** auto-retry (duplicate risk) |
| Rate limit 429 | Surface retryable error |
| Mock mode / incomplete config | Simulate call, label `is_mock=true` |

## Inbound calls

Inbound routing depends on phone-number assignment inside the Edesy workspace. This app documents outbound/test calling. Do not claim inbound works until a number is linked to the agent in Edesy and verified manually.
