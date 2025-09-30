"""FastAPI application exposing Azure Voice Live backed assistant."""

from __future__ import annotations

import logging
import os
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    logger.debug("python-dotenv not installed; skipping .env loading")

from .assistant import MockAssistant
from .schemas import InteractionRequest, InteractionResponse
from .settings import VoiceLiveSettings
from .voicelive import VoiceLiveBridge

app = FastAPI(title="Voice Assistant Demo", version="0.2.0")
assistant = MockAssistant()
voicelive_settings = VoiceLiveSettings.from_env()

allowed_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> Dict[str, str]:
    """Simple probe endpoint for container orchestrators."""
    return {"status": "ok"}


@app.post("/interaction", response_model=InteractionResponse, tags=["assistant"])
async def interaction(payload: InteractionRequest) -> InteractionResponse:
    """Fallback text-based interaction using the mock assistant."""
    result = assistant.handle_interaction(payload.message)
    return InteractionResponse(**result)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    bridge = VoiceLiveBridge(websocket=websocket, settings=voicelive_settings)

    try:
        await bridge.run()
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error in WebSocket loop: %s", exc)
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": "Server error occurred"})
    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
