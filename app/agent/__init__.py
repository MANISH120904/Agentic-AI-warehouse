"""Google ADK warehouse voice agent package.

Run from repo root:
  adk web --port 8035

Then select the `agent` folder under `app/`. This browser voice path is
separate from Edesy PSTN calls.
"""

from .agent import root_agent

__all__ = ["root_agent"]
