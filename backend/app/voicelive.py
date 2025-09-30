"""Session bridge between client WebSocket and Azure Voice Live."""

from __future__ import annotations

import asyncio
import base64
import datetime
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Tuple, Union

from fastapi import WebSocket

from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioInputTranscriptionSettings,
    AzureStandardVoice,
    FunctionCallOutputItem,
    FunctionTool,
    InputAudioFormat,
    ItemType,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ResponseFunctionCallItem,
    ServerEventConversationItemCreated,
    ServerEventResponseFunctionCallArgumentsDone,
    ServerEventType,
    ServerVad,
    Tool,
    ToolChoiceLiteral,
)

from .settings import VoiceLiveSettings

logger = logging.getLogger(__name__)

JsonDict = Dict[str, Any]


async def _wait_for_event(
    conn,
    wanted_types: set[ServerEventType],
    *,
    timeout_s: float = 10.0,
    on_unhandled: Optional[Callable[[Any], Awaitable[None]]] = None,
):
    """Utility helper to block until a specific event type arrives."""

    async def _next():
        while True:
            evt = await conn.recv()
            if evt.type in wanted_types:
                return evt
            if on_unhandled:
                await on_unhandled(evt)

    return await asyncio.wait_for(_next(), timeout=timeout_s)


class VoiceLiveBridge:
    """Bridges a FastAPI WebSocket with the Azure Voice Live streaming session."""

    def __init__(self, websocket: WebSocket, settings: VoiceLiveSettings):
        self.websocket = websocket
        self.settings = settings
        self._connection = None
        self._stopped = asyncio.Event()

        self.function_call_in_progress: bool = False
        self.active_call_id: Optional[str] = None
        self.session_ready: bool = False

        self._user_transcripts: Dict[str, str] = {}
        self._assistant_transcripts: Dict[Tuple[str, str, int], str] = {}
        self._assistant_text: Dict[str, str] = {}

        self.available_functions: Dict[
            str, Callable[[Union[str, Mapping[str, Any]]], Mapping[str, Any]]
        ] = {
            "get_current_time": self.get_current_time,
            "get_current_weather": self.get_current_weather,
        }

    async def run(self) -> None:
        """Entry point for a single client session."""

        async with self.settings.credential_context() as credential:
            async with connect(
                endpoint=self.settings.endpoint,
                credential=credential,
                model=self.settings.model,
            ) as connection:
                self._connection = connection
                await self._configure_session()

                await self.websocket.send_json(
                    {
                        "type": "system_message",
                        "text": "Connected to Azure Voice Live. You can start speaking!",
                    }
                )

                event_task = asyncio.create_task(self._process_events())
                client_task = asyncio.create_task(self._process_client_messages())

                done, pending = await asyncio.wait(
                    {event_task, client_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                self._stopped.set()

                for task in pending:
                    task.cancel()
                for task in done:
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    async def _configure_session(self) -> None:
        """Send the initial session configuration to Azure Voice Live."""

        voice_config = AzureStandardVoice(name=self.settings.voice)
        turn_detection = ServerVad(threshold=0.5, prefix_padding_ms=300, silence_duration_ms=500)

        function_tools: list[Tool] = [
            FunctionTool(
                name="get_current_time",
                description="Get the current time",
                parameters={
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone to get the current time for, e.g., 'UTC', 'local'",
                        }
                    },
                    "required": [],
                },
            ),
            FunctionTool(
                name="get_current_weather",
                description="Get the current weather in a given location",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g., 'San Francisco, CA'",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The unit of temperature to use",
                        },
                    },
                    "required": ["location"],
                },
            ),
        ]

        session = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=self.settings.instructions,
            voice=voice_config,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            input_audio_echo_cancellation=AudioEchoCancellation(),
            turn_detection=turn_detection,
            tools=function_tools,
            tool_choice=ToolChoiceLiteral.AUTO,
            input_audio_transcription=AudioInputTranscriptionSettings(model="whisper-1"),
        )

        await self._connection.session.update(session=session)

    async def _process_client_messages(self) -> None:
        """Receive audio chunks from the browser and forward them to Azure."""

        while not self._stopped.is_set():
            try:
                message = await self.websocket.receive()
            except Exception:  # fastapi raises different errors on disconnect
                break

            if "text" in message and message["text"] is not None:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await self.websocket.send_json(
                        {"type": "error", "message": "Invalid payload received"}
                    )
                    continue
            elif "bytes" in message and message["bytes"] is not None:
                encoded = base64.b64encode(message["bytes"]).decode("utf-8")
                data = {"type": "audio_chunk", "audio": encoded}
            else:
                # keep-alive frame
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await self.websocket.send_json({"type": "pong"})
                continue

            if msg_type == "stop":
                logger.info("Client requested stop")
                if self._connection and self.session_ready:
                    try:
                        await self._connection.response.cancel()
                    except Exception as exc:  # pragma: no cover - best effort
                        logger.debug("No active response to cancel: %s", exc)
                break

            if msg_type != "audio_chunk":
                await self.websocket.send_json(
                    {"type": "error", "message": f"Unsupported message type: {msg_type}"}
                )
                continue

            audio_payload = data.get("audio")
            if not isinstance(audio_payload, str):
                await self.websocket.send_json(
                    {"type": "error", "message": "Audio payload missing or invalid"}
                )
                continue

            try:
                await self._connection.input_audio_buffer.append(audio=audio_payload)
            except Exception as exc:  # pragma: no cover - service level error
                logger.exception("Failed to forward audio to Azure: %s", exc)
                await self.websocket.send_json(
                    {"type": "error", "message": "Unable to forward audio to assistant"}
                )
                continue

            sequence = data.get("sequence")
            await self.websocket.send_json({"type": "ack", "sequence": sequence})

    async def _process_events(self) -> None:
        """Listen for events from Azure Voice Live and relay them to the client."""

        try:
            while not self._stopped.is_set():
                event = await self._connection.recv()
                await self._handle_event(event)
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
            raise
        except Exception as exc:  # pragma: no cover - log and propagate
            logger.exception("Voice Live event loop terminated: %s", exc)
            await self.websocket.send_json(
                {"type": "error", "message": "Azure Voice Live connection ended unexpectedly"}
            )

    async def _handle_event(self, event) -> None:  # noqa: C901 - complex event handler
        ap_sample_rate = self.settings.sample_rate_hz

        if event.type == ServerEventType.SESSION_UPDATED:
            self.session_ready = True
            await self.websocket.send_json({"type": "assistant_state", "state": "ready"})
            return

        if event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            await self.websocket.send_json({"type": "assistant_state", "state": "listening"})
            return

        if event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            await self.websocket.send_json({"type": "assistant_state", "state": "processing"})
            return

        if event.type == ServerEventType.RESPONSE_CREATED:
            response_id = getattr(event, "response_id", None)
            if response_id:
                self._assistant_text[response_id] = ""
            return

        if event.type == ServerEventType.RESPONSE_TEXT_DELTA:
            response_id = getattr(event, "response_id", None)
            if response_id:
                existing = self._assistant_text.get(response_id, "")
                delta = getattr(event, "delta", "") or ""
                self._assistant_text[response_id] = existing + delta
            return

        if event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            delta = getattr(event, "delta", None)
            if not delta:
                return
            encoded = base64.b64encode(delta).decode("utf-8")
            await self.websocket.send_json(
                {
                    "type": "assistant_audio",
                    "audio": encoded,
                    "format": "pcm16",
                    "sampleRate": ap_sample_rate,
                }
            )
            await self.websocket.send_json({"type": "assistant_state", "state": "speaking"})
            return

        if event.type == ServerEventType.RESPONSE_AUDIO_DONE:
            await self.websocket.send_json({"type": "assistant_state", "state": "processing"})
            return

        if event.type == ServerEventType.RESPONSE_DONE:
            response_id = getattr(event, "response_id", None)
            text = ""
            if response_id:
                text = self._assistant_text.pop(response_id, "")
            transcript = getattr(event, "transcript", None)
            if not text:
                text = transcript or "Assistant response completed."

            await self.websocket.send_json(
                {
                    "type": "assistant_message",
                    "text": text,
                    "transcript": transcript,
                }
            )
            self.function_call_in_progress = False
            self.active_call_id = None
            await self.websocket.send_json({"type": "assistant_state", "state": "idle"})
            return

        if event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            if not self.settings.show_transcriptions:
                return
            item_id = getattr(event, "item_id", None)
            transcript = getattr(event, "transcript", "")
            if item_id and transcript:
                self._user_transcripts[item_id] = transcript
                await self.websocket.send_json(
                    {"type": "user_transcript", "text": transcript, "item_id": item_id}
                )
            return

        if event.type == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_FAILED:
            error = getattr(event, "error", None)
            message = getattr(error, "message", None) if error else None
            await self.websocket.send_json(
                {
                    "type": "error",
                    "message": message or "Unable to transcribe your last utterance.",
                }
            )
            return

        if event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            if not self.settings.show_transcriptions:
                return
            key = (
                getattr(event, "response_id", ""),
                getattr(event, "item_id", ""),
                getattr(event, "output_index", -1),
            )
            if not key[0] or not key[1] or key[2] < 0:
                return
            delta = getattr(event, "delta", "") or ""
            current = self._assistant_transcripts.get(key, "") + delta
            self._assistant_transcripts[key] = current
            return

        if event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
            if not self.settings.show_transcriptions:
                return
            key = (
                getattr(event, "response_id", ""),
                getattr(event, "item_id", ""),
                getattr(event, "output_index", -1),
            )
            transcript = getattr(event, "transcript", "")
            if not transcript:
                transcript = self._assistant_transcripts.get(key, "")
            if transcript:
                await self.websocket.send_json(
                    {
                        "type": "assistant_transcript",
                        "text": transcript,
                        "response_id": key[0],
                    }
                )
            self._assistant_transcripts.pop(key, None)
            return

        if event.type == ServerEventType.ERROR:
            err = getattr(event, "error", None)
            message = getattr(err, "message", None) if err else "Voice assistant error"
            await self.websocket.send_json({"type": "error", "message": message})
            return

        if event.type == ServerEventType.CONVERSATION_ITEM_CREATED:
            if isinstance(event, ServerEventConversationItemCreated) and isinstance(
                event.item, ResponseFunctionCallItem
            ):
                await self.websocket.send_json(
                    {
                        "type": "assistant_state",
                        "state": "function_call",
                        "function": event.item.name,
                    }
                )
                await self._handle_function_call(event)
            return

        # Fallback logging for unhandled types for troubleshooting.
        logger.debug("Unhandled Voice Live event: %s", event)

    async def _handle_function_call(self, conversation_created_event) -> None:
        if not isinstance(conversation_created_event, ServerEventConversationItemCreated):
            return
        if not isinstance(conversation_created_event.item, ResponseFunctionCallItem):
            return

        function_call_item = conversation_created_event.item
        function_name = function_call_item.name
        call_id = function_call_item.call_id
        previous_item_id = function_call_item.id

        logger.info("Function call requested: %s", function_name)
        self.function_call_in_progress = True
        self.active_call_id = call_id

        async def _forward(evt):
            await self._handle_event(evt)

        try:
            function_done = await _wait_for_event(
                self._connection,
                {ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE},
                on_unhandled=_forward,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for function arguments for %s", function_name)
            return

        if not isinstance(function_done, ServerEventResponseFunctionCallArgumentsDone):
            logger.error("Unexpected event while waiting for function arguments: %s", function_done)
            return

        arguments = function_done.arguments

        if function_done.call_id != call_id:
            logger.warning("Function call ID mismatch: %s vs %s", function_done.call_id, call_id)
            return

        try:
            response_done_event = await _wait_for_event(
                self._connection,
                {ServerEventType.RESPONSE_DONE},
                on_unhandled=_forward,
            )
            await self._handle_event(response_done_event)
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for response completion after function %s", function_name)

        if function_name in self.available_functions:
            try:
                result = self.available_functions[function_name](arguments)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Function %s execution failed: %s", function_name, exc)
                result = {"error": str(exc)}
        else:
            result = {"error": f"Unknown function {function_name}"}

        output_item = FunctionCallOutputItem(call_id=call_id, output=json.dumps(result))
        await self._connection.conversation.item.create(
            previous_item_id=previous_item_id,
            item=output_item,
        )
        await self._connection.response.create()

    # ------------------------------------------------------------------
    # Example function implementations copied from the sample
    # ------------------------------------------------------------------

    def get_current_time(
        self, arguments: Optional[Union[str, Mapping[str, Any]]] = None
    ) -> Mapping[str, Any]:
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError:
                args = {}
        elif isinstance(arguments, Mapping):
            args = arguments
        else:
            args = {}

        timezone = str(args.get("timezone", "local"))
        now = datetime.datetime.now(datetime.timezone.utc if timezone.lower() == "utc" else None)
        timezone_name = "UTC" if timezone.lower() == "utc" else "local"

        return {
            "time": now.strftime("%I:%M:%S %p"),
            "date": now.strftime("%A, %B %d, %Y"),
            "timezone": timezone_name,
        }

    def get_current_weather(self, arguments: Union[str, Mapping[str, Any], None]) -> Mapping[str, Any]:
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError:
                logger.error("Failed to parse weather arguments: %s", arguments)
                return {"error": "Invalid arguments"}
        elif isinstance(arguments, Mapping):
            args = arguments
        else:
            return {"error": "No arguments provided"}

        location = str(args.get("location", "Unknown"))
        unit = str(args.get("unit", "celsius"))

        temperature = 22 if unit == "celsius" else 72
        return {
            "location": location,
            "temperature": temperature,
            "unit": unit,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 10,
        }
