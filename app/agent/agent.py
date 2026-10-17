"""Google ADK root agent for browser voice demos."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from google.adk.agents import Agent

from app.agent.prompts import WAREHOUSE_AGENT_INSTRUCTION
from app.agent.tools import WAREHOUSE_TOOLS

# Prefer env override; keep a documented Live-oriented default for demos.
_MODEL = os.getenv(
    "ADK_MODEL",
    "gemini-2.5-flash-native-audio-preview-09-2025",
)

root_agent = Agent(
    name="warehouse_voice_agent",
    model=_MODEL,
    description=(
        "Warehouse and delivery support assistant with tools for orders, "
        "inventory, delay risk, feedback, and customer history."
    ),
    instruction=WAREHOUSE_AGENT_INSTRUCTION,
    tools=WAREHOUSE_TOOLS,
)
