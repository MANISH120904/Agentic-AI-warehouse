"""WarehouseVoiceAI operator dashboard (Streamlit).

All business logic is fetched from the FastAPI backend — no secrets in the UI.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from uuid import uuid4

import httpx
import streamlit as st

API_BASE = os.getenv("WAREHOUSE_API_BASE", "http://127.0.0.1:8765")

st.set_page_config(
    page_title="WarehouseVoiceAI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --wv-bg: #f7f5f3;
        --wv-ink: #1c1917;
        --wv-muted: #57534e;
        --wv-accent: #c2410c;
        --wv-card: #ffffff;
        --wv-border: #e7e5e4;
      }
      .stApp { background: linear-gradient(180deg, #faf7f4 0%, #f0ebe6 100%); color: var(--wv-ink); }
      h1, h2, h3 { color: var(--wv-ink) !important; letter-spacing: -0.02em; }
      .wv-card {
        background: var(--wv-card);
        border: 1px solid var(--wv-border);
        border-radius: 16px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 1px 2px rgba(28,25,23,0.04);
        margin-bottom: 0.75rem;
      }
      .wv-metric { font-size: 1.8rem; font-weight: 700; color: var(--wv-ink); }
      .wv-label { color: var(--wv-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
      .wv-badge {
        display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
        font-size: 0.75rem; font-weight: 600;
      }
      .wv-badge-ok { background: #dcfce7; color: #166534; }
      .wv-badge-warn { background: #ffedd5; color: #9a3412; }
      .wv-badge-bad { background: #fee2e2; color: #991b1b; }
      .wv-badge-mock { background: #e0e7ff; color: #3730a3; }
      .wv-brand { font-size: 1.6rem; font-weight: 800; color: var(--wv-accent); }
      div[data-testid="stSidebar"] { background: #fffaf7; border-right: 1px solid var(--wv-border); }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str) -> Any:
    with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
        response = client.get(path)
        response.raise_for_status()
        return response.json()


def api_post(path: str, payload: dict[str, Any]) -> tuple[int, Any]:
    with httpx.Client(base_url=API_BASE, timeout=60.0) as client:
        response = client.post(path, json=payload)
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = {"detail": response.text}
        return response.status_code, body


def badge(text: str, kind: str = "ok") -> str:
    return f'<span class="wv-badge wv-badge-{kind}">{text}</span>'


def risk_badge(risk: str) -> str:
    kind = {"low": "ok", "medium": "warn", "high": "bad"}.get(risk, "warn")
    return badge(risk.upper(), kind)


PAGES = [
    "Overview",
    "Local Voice",
    "Orders",
    "Inventory",
    "Make a Call",
    "Call History",
    "Feedback",
    "Settings",
]

with st.sidebar:
    st.markdown('<div class="wv-brand">WarehouseVoiceAI</div>', unsafe_allow_html=True)
    st.caption("Operator dashboard · simulated warehouse data")
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption(f"API: `{API_BASE}`")


def render_overview() -> None:
    st.title("Overview")
    st.caption("Live snapshot from the FastAPI backend.")
    try:
        summary = api_get("/api/dashboard/summary")
        health = api_get("/health")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Backend unavailable at {API_BASE}: {exc}")
        return

    cols = st.columns(5)
    metrics = [
        ("Total orders", summary["total_orders"]),
        ("High-risk shipments", summary["high_risk_shipments"]),
        ("Calls completed", summary["calls_completed"]),
        ("Calls failed", summary["calls_failed"]),
        ("Feedback count", summary["feedback_count"]),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="wv-card"><div class="wv-label">{label}</div>'
                f'<div class="wv-metric">{value}</div></div>',
                unsafe_allow_html=True,
            )

    mode = "MOCK" if health.get("mock_mode") else "LIVE"
    st.markdown(
        f'{badge(mode, "mock" if mode == "MOCK" else "warn")} '
        f'{badge("Edesy ready" if health.get("telephony_ready") else "Edesy not ready", "ok" if health.get("telephony_ready") else "warn")}',
        unsafe_allow_html=True,
    )
    if summary.get("average_rating") is not None:
        st.write(f"Average satisfaction: **{summary['average_rating']}** / 5")

    st.subheader("Recent call activity")
    recent = summary.get("recent_calls") or []
    if not recent:
        st.info("No calls yet. Place a mock call from **Make a Call**.")
    else:
        for call in recent:
            mock = badge("MOCK", "mock") if call.get("is_mock") else badge("LIVE", "warn")
            st.markdown(
                f'<div class="wv-card">{mock} <strong>{call.get("call_id")}</strong> · '
                f'{call.get("phone_number")} · {call.get("status")} · {call.get("purpose")}</div>',
                unsafe_allow_html=True,
            )


def render_local_voice() -> None:
    st.title("Local Voice Agent")
    st.caption(
        "Talk to the Google ADK browser agent. It uses tools against the local SQLite DB "
        "on this machine — no cloud warehouse database required."
    )

    try:
        db = api_get("/api/local/db")
        settings = api_get("/api/settings")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Backend unavailable: {exc}")
        return

    st.markdown(
        f'<div class="wv-card">'
        f'{badge("LOCAL DB", "ok")} '
        f'<code>{db.get("db_path")}</code><br/>'
        f'Orders: {db.get("counts", {}).get("orders", 0)} · '
        f'Inventory: {db.get("counts", {}).get("inventory", 0)} · '
        f'Shipments: {db.get("counts", {}).get("shipments", 0)}'
        f"</div>",
        unsafe_allow_html=True,
    )

    if settings.get("google_configured"):
        st.success("GOOGLE_API_KEY is configured — ADK can start.")
    else:
        st.warning(
            "Set GOOGLE_API_KEY in your local `.env`, then restart the API. "
            "Voice needs a Gemini Live-capable key."
        )

    st.subheader("How to talk with local data")
    st.markdown(
        """
1. Keep this FastAPI backend running (local SQLite is already seeded).
2. In a new terminal from the repo:

```powershell
.\.venv\Scripts\Activate.ps1
$env:SSL_CERT_FILE = (python -m certifi)
cd app
adk web --port 8035
```

3. Open the ADK URL, select **agent** / `warehouse_voice_agent`, reload, click the mic.
4. Try: *“What is the status of order ORD-1001?”* or *“Is SKU-B210 low on stock?”*
        """
    )

    st.subheader("Prove tools hit the local DB")
    col1, col2 = st.columns(2)
    with col1:
        order_id = st.text_input("Order ID", value="ORD-1001", key="lv_order")
        if st.button("Lookup order via API"):
            status, body = api_post(
                "/api/tools/get_order_status", {"order_id": order_id}
            )
            if status >= 400:
                st.error(body)
            else:
                st.json(body)
    with col2:
        product_id = st.text_input("Product ID", value="SKU-B210", key="lv_sku")
        if st.button("Lookup inventory via API"):
            status, body = api_post(
                "/api/tools/get_inventory", {"product_id": product_id}
            )
            if status >= 400:
                st.error(body)
            else:
                st.json(body)

    st.info(
        "Phone (Edesy) is optional and separate. Local spoken answers use ADK + this SQLite file."
    )


def render_orders() -> None:
    st.title("Orders")
    query = st.text_input("Search order ID", placeholder="ORD-1001")
    try:
        orders = api_get("/api/orders")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load orders: {exc}")
        return

    if query:
        orders = [o for o in orders if query.upper() in o["order_id"].upper()]

    if not orders:
        st.warning("No matching orders.")
        return

    for order in orders:
        delay = None
        try:
            delay = api_get(f"/api/orders/{order['order_id']}/delay-risk")
        except Exception:  # noqa: BLE001
            delay = None
        risk_html = risk_badge(delay["risk"]) if delay else ""
        reasons = ", ".join(delay.get("reasons", [])[:2]) if delay else ""
        st.markdown(
            f'<div class="wv-card"><strong>{order["order_id"]}</strong> · {order["customer_name"]} '
            f'{risk_html}<br/>Status: {order["status"]} · ETA: {order["estimated_delivery"]} · '
            f'Warehouse: {order["warehouse"]}<br/>'
            f'<span style="color:#57534e">{reasons}</span></div>',
            unsafe_allow_html=True,
        )


def render_inventory() -> None:
    st.title("Inventory")
    query = st.text_input("Search product ID or name", placeholder="SKU-B210")
    try:
        items = api_get("/api/inventory")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load inventory: {exc}")
        return

    if query:
        q = query.lower()
        items = [
            i
            for i in items
            if q in i["product_id"].lower() or q in i["product_name"].lower()
        ]

    for item in items:
        low = item["quantity_available"] <= item["reorder_threshold"]
        flag = badge("LOW STOCK", "bad") if low else badge("OK", "ok")
        st.markdown(
            f'<div class="wv-card">{flag} <strong>{item["product_id"]}</strong> — '
            f'{item["product_name"]}<br/>Warehouse: {item["warehouse"]} · '
            f'Qty: <strong>{item["quantity_available"]}</strong> '
            f'(reorder at {item["reorder_threshold"]})</div>',
            unsafe_allow_html=True,
        )


def render_make_call() -> None:
    st.title("Make a Call")
    st.caption("Requires explicit confirmation. Mock mode never places a real call.")

    try:
        health = api_get("/health")
        orders = api_get("/api/orders")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Backend unavailable: {exc}")
        return

    if health.get("mock_mode"):
        st.info("MOCK_MODE is enabled. Calls will be simulated and labeled as mock.")
    elif not health.get("telephony_ready"):
        st.warning("Telephony is not ready. Configure Edesy key + agent id, or keep MOCK_MODE.")

    order_ids = [""] + [o["order_id"] for o in orders]
    phone = st.text_input("Customer phone number", placeholder="+919876543210")
    order_id = st.selectbox("Order ID (optional)", order_ids)
    purpose = st.selectbox(
        "Call purpose",
        ["order_status", "delay_update", "delivery_confirmation", "feedback_followup"],
    )

    st.subheader("Preview")
    st.write(
        {
            "phone_number": phone or "(missing)",
            "order_id": order_id or None,
            "purpose": purpose,
            "mode": "MOCK" if health.get("mock_mode") else "LIVE",
        }
    )

    confirm = st.checkbox("I confirm I want to place this call")
    if "idempotency_key" not in st.session_state:
        st.session_state.idempotency_key = str(uuid4())

    if st.button("Place call", type="primary", disabled=not confirm or not phone):
        status, body = api_post(
            "/api/calls/outbound",
            {
                "phone_number": phone,
                "order_id": order_id or None,
                "purpose": purpose,
                "confirm": True,
                "idempotency_key": st.session_state.idempotency_key,
            },
        )
        if status >= 400:
            detail = body.get("detail", body)
            st.error(detail)
        else:
            st.success(body.get("message", "Call submitted"))
            st.json(body.get("call"))
            st.session_state.idempotency_key = str(uuid4())


def render_call_history() -> None:
    st.title("Call History")
    try:
        calls = api_get("/api/calls")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load calls: {exc}")
        return

    if not calls:
        st.info("No calls recorded yet.")
        return

    for call in calls:
        mock = badge("MOCK", "mock") if call.get("is_mock") else badge("LIVE", "warn")
        with st.expander(f"{call['call_id']} · {call.get('status')} · {call.get('phone_number')}"):
            st.markdown(mock, unsafe_allow_html=True)
            st.write(
                {
                    "call_id": call.get("call_id"),
                    "conversation_id": call.get("conversation_id"),
                    "phone": call.get("phone_number"),
                    "status": call.get("status"),
                    "duration": call.get("duration"),
                    "outcome": call.get("outcome"),
                    "order_id": call.get("order_id"),
                    "error": call.get("error"),
                }
            )
            if call.get("transcript"):
                st.text(call["transcript"])
            if not call.get("is_mock") and call.get("conversation_id"):
                if st.button("Refresh from Edesy", key=f"refresh-{call['call_id']}"):
                    status, body = api_post(f"/api/calls/{call['call_id']}/refresh", {})
                    if status >= 400:
                        st.error(body)
                    else:
                        st.success("Refreshed")
                        st.json(body)


def render_feedback() -> None:
    st.title("Feedback")
    try:
        rows = api_get("/api/feedback")
        summary = api_get("/api/dashboard/summary")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load feedback: {exc}")
        return

    if summary.get("average_rating") is not None:
        st.metric("Average rating", f"{summary['average_rating']} / 5")
    else:
        st.caption("No ratings yet.")

    with st.form("add_feedback"):
        st.subheader("Record feedback")
        call_id = st.text_input("Call ID (optional)")
        rating = st.slider("Rating", 1, 5, 4)
        comment = st.text_area("Comment")
        submitted = st.form_submit_button("Save")
        if submitted:
            status, body = api_post(
                "/api/feedback",
                {
                    "call_id": call_id or None,
                    "rating": rating,
                    "feedback": comment,
                },
            )
            if status >= 400:
                st.error(body)
            else:
                st.success("Feedback saved")
                st.rerun()

    for row in rows:
        st.markdown(
            f'<div class="wv-card"><strong>{"★" * int(row["rating"])}</strong> · '
            f'{row.get("call_id") or "no call"} · {row.get("created_at")}<br/>'
            f'{row.get("feedback")}</div>',
            unsafe_allow_html=True,
        )


def render_settings() -> None:
    st.title("Settings")
    st.caption("Secrets are never shown in full.")
    try:
        settings = api_get("/api/settings")
        health = api_get("/health")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Backend unavailable: {exc}")
        return

    st.markdown(
        f'<div class="wv-card">'
        f'<div>Mock mode: <strong>{settings["mock_mode"]}</strong></div>'
        f'<div>Edesy configured: <strong>{settings["edesy_configured"]}</strong> '
        f'({settings["edesy_api_key_masked"]})</div>'
        f'<div>Google ADK configured: <strong>{settings["google_configured"]}</strong> '
        f'({settings["google_api_key_masked"]})</div>'
        f'<div>Telephony ready: <strong>{settings["telephony_ready"]}</strong></div>'
        f'<div>Base URL: <code>{settings["edesy_api_base_url"]}</code></div>'
        f'<div>Agent ID: <code>{settings["edesy_agent_id"]}</code></div>'
        f'<div>Public base URL: <code>{settings["public_base_url"]}</code></div>'
        f'<div>ADK model: <code>{settings["adk_model"]}</code></div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    for note in settings.get("notes", []):
        st.write(f"- {note}")

    if st.button("Check Edesy connectivity"):
        try:
            status = api_get("/api/edesy/status")
            st.json(status)
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    st.info(
        "Browser voice agent: run `adk web` separately. It is not connected to PSTN audio."
    )
    st.json(health)


PAGE_RENDERERS = {
    "Overview": render_overview,
    "Local Voice": render_local_voice,
    "Orders": render_orders,
    "Inventory": render_inventory,
    "Make a Call": render_make_call,
    "Call History": render_call_history,
    "Feedback": render_feedback,
    "Settings": render_settings,
}

PAGE_RENDERERS[page]()
