# infrastructure/livekit/adapter.py
"""
LiveKitAdapter
==============

Infrastructure-layer adapter that wraps the ``livekit-server-sdk`` and
implements the three methods required by the LiveKitPort Protocol used in
use‑case layer.

It purposefully keeps only the minimal surface needed by the application so
that the core business rules stay decoupled from the third‑party SDK.
"""

from __future__ import annotations

from typing import Any

try:
    from livekit.api import LiveKitAPI, AccessToken
except ImportError:
    # Fallback for development
    LiveKitAPI = None
    AccessToken = None


class LiveKitAdapter:
    """
    A thin wrapper around LiveKit's RoomServiceClient + JWT builder.

    Methods correspond exactly to the LiveKitPort protocol:

    * ``create_room_if_not_exists``
    * ``build_access_token``
    * ``delete_room``
    """

    def __init__(self, host: str, api_key: str, api_secret: str) -> None:
        if LiveKitAPI:
            self._svc = LiveKitAPI(host, api_key, api_secret)
        else:
            self._svc = None
        self._api_key = api_key
        self._api_secret = api_secret

    # --------------------------------------------------------------------- #
    # LiveKitPort impl
    # --------------------------------------------------------------------- #
    def create_room_if_not_exists(self, room_name: str) -> None:
        """
        LiveKit `create_room` is idempotent – error on duplicate names.
        We swallow *already exists* errors to comply with our use‑case
        contract (room must exist after the call).
        """
        try:
            self._svc.room.create_room(name=room_name)
        except Exception as exc:  # noqa: BLE001
            # LiveKit raises generic Exception; check message
            if "already exists" not in str(exc).lower():
                raise

    def build_access_token(
        self,
        room: str,
        identity: str,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str:
        """
        Generate a JWT for LiveKit signalling WS.
        """
        token = AccessToken(self._api_key, self._api_secret, identity=identity)
        grants: dict[str, Any] = {"room": room, "roomJoin": True}
        if can_publish:
            grants["canPublish"] = True
        if can_subscribe:
            grants["canSubscribe"] = True
        token.add_grant(grants)
        return token.to_jwt()

    def delete_room(self, room_name: str) -> None:  # noqa: D401
        """
        Hard‑delete a room; swallow 404 if the room is already gone.
        """
        try:
            self._svc.room.delete_room(room=room_name)
        except Exception as exc:  # noqa: BLE001
            if "not found" not in str(exc).lower():
                raise

# infrastructure/livekit/agent.py
"""
HostAgent
=========

A LiveKit Agent that joins the room as a hidden participant, chats with
User A, and calls the ``invite_user`` tool when the InvitationPolicy is met.
"""

import os
from typing import Any

try:
    from livekit.agents import Agent, RunContext, function_tool
    from livekit.plugins import openai  # type: ignore
except ImportError:
    # Fallback for development
    Agent = None
    RunContext = None
    function_tool = None
    openai = None


ORCHESTRATOR_URL = os.getenv("ORCH_URL", f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost:8000')}")


class HostAgent:
    system_prompt_path = os.path.join(
        os.path.dirname(__file__), "prompts", "host_system.txt"
    )

    def __init__(self) -> None:
        # Mock initialization for development
        pass

    # ------------------------------------------------------------------ #
    # Function tool exposed to the LLM
    # ------------------------------------------------------------------ #
    async def invite_user(
        self, context, identity: str, reason: str | None = None
    ) -> str:  # noqa: D401
        """
        Called by the LLM when it's time to bring User B into the room.
        """
        # Mock implementation for development
        return "ok"

# infrastructure/livekit/runner.py
"""
runner.py
=========

Entry‑point script to start HostAgent and connect it to LiveKit Cloud.
"""

import asyncio
import os

try:
    from livekit.agents import AgentSession
    from livekit.plugins import openai  # type: ignore
except ImportError:
    # Fallback for development
    AgentSession = None
    openai = None

# from .agent import HostAgent


async def _main() -> None:
    # ------------------------------------------------------------------ #
    # Read environment variables
    # ------------------------------------------------------------------ #
    if not AgentSession:
        print("LiveKit not available - mock mode")
        return
    
    ws_url = os.environ["LK_WSS"]
    token = os.environ["AGENT_TOKEN"]

    # Agent instantiation
    agent = HostAgent()

    # Speech pipeline
    session = AgentSession(
        ws_url=ws_url,
        token=token,
        agent=agent,
        stt=openai.STT(model="gpt-4o-transcribe"),
        tts=openai.TTS(model="gpt-4o-mini-tts", voice="alloy"),
    )
    await session.run()


if __name__ == "__main__":
    asyncio.run(_main())
