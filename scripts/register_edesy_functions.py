#!/usr/bin/env python3
"""Register warehouse HTTP tools on a hosted Edesy agent.

Requires:
  - EDESY_API_KEY
  - EDESY_AGENT_ID
  - PUBLIC_BASE_URL (HTTPS URL reachable by Edesy)

This does NOT connect Google ADK audio to the phone call. It only lets the
hosted Edesy agent call your FastAPI tool endpoints mid-conversation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.edesy_service import EdesyError, EdesyService

TOOLS = [
    {
        "name": "get_order_status",
        "description": (
            "Look up a warehouse order status. Call as soon as the customer "
            "provides an order number such as ORD-1001."
        ),
        "parametersSchema": {
            "order_id": {"type": "string", "description": "Order ID, e.g. ORD-1001"}
        },
        "requiredParams": ["order_id"],
        "path": "/api/tools/get_order_status",
        "httpBody": '{"order_id": "{{order_id}}"}',
    },
    {
        "name": "get_inventory",
        "description": "Look up inventory quantity for a product SKU.",
        "parametersSchema": {
            "product_id": {"type": "string", "description": "Product ID, e.g. SKU-A100"}
        },
        "requiredParams": ["product_id"],
        "path": "/api/tools/get_inventory",
        "httpBody": '{"product_id": "{{product_id}}"}',
    },
    {
        "name": "predict_delivery_delay",
        "description": (
            "Estimate simulated delivery delay risk for an order. "
            "Results are heuristic, not a live carrier ETA."
        ),
        "parametersSchema": {
            "order_id": {"type": "string", "description": "Order ID"}
        },
        "requiredParams": ["order_id"],
        "path": "/api/tools/predict_delivery_delay",
        "httpBody": '{"order_id": "{{order_id}}"}',
    },
    {
        "name": "record_customer_feedback",
        "description": "Record customer feedback with a 1-5 rating after confirmation.",
        "parametersSchema": {
            "call_id": {"type": "string", "description": "Call or conversation id"},
            "rating": {"type": "integer", "description": "Rating from 1 to 5"},
            "feedback": {"type": "string", "description": "Customer comment"},
        },
        "requiredParams": ["rating", "feedback"],
        "path": "/api/tools/record_customer_feedback",
        "httpBody": (
            '{"call_id": "{{call_id}}", "rating": {{rating}}, '
            '"feedback": "{{feedback}}"}'
        ),
    },
    {
        "name": "get_customer_order_history",
        "description": "List simulated orders for a customer id such as CUST-501.",
        "parametersSchema": {
            "customer_id": {"type": "string", "description": "Customer ID"}
        },
        "requiredParams": ["customer_id"],
        "path": "/api/tools/get_customer_order_history",
        "httpBody": '{"customer_id": "{{customer_id}}"}',
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirm")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.edesy_api_key or settings.edesy_agent_id is None:
        print("ERROR: Set EDESY_API_KEY and EDESY_AGENT_ID first.")
        return 1
    if not settings.public_base_url.startswith("https://"):
        print(
            "ERROR: PUBLIC_BASE_URL must be a public HTTPS URL "
            "(localhost will not work for Edesy tool calls)."
        )
        return 1

    print(f"Agent ID: {settings.edesy_agent_id}")
    print(f"Public base: {settings.public_base_url}")
    if not args.yes:
        answer = input("Register HTTP tools on this agent? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 0

    base = settings.public_base_url.rstrip("/")
    with EdesyService(settings) as edesy:
        for tool in TOOLS:
            try:
                created = edesy.register_http_function(
                    agent_id=int(settings.edesy_agent_id),
                    name=tool["name"],
                    description=tool["description"],
                    parameters_schema=tool["parametersSchema"],
                    required_params=tool["requiredParams"],
                    http_method="POST",
                    http_url=f"{base}{tool['path']}",
                    http_body=tool["httpBody"],
                )
                print(f"OK  {tool['name']} -> id={created.get('id')}")
            except EdesyError as exc:
                print(f"FAIL {tool['name']}: {exc.code} {exc.message}")
                return 1
    print("Done. Hosted Edesy agent can now call these FastAPI tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
