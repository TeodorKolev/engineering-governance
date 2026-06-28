import asyncio
import os

_DELAY = float(os.environ.get("INTER_AGENT_DELAY_SECONDS", "12"))

async def throttle_after_agent(callback_context) -> None:
    """Sleep between sequential specialist agents to avoid TPM bursts on the free tier.
    Override delay via INTER_AGENT_DELAY_SECONDS env var (set to 0 on paid tiers)."""
    if _DELAY > 0:
        await asyncio.sleep(_DELAY)
