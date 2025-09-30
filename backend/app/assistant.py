"""Simple rule-based assistant used as a placeholder for real AI logic."""

from __future__ import annotations

import datetime
import json
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from .audio import generate_tone_wav


_GREETINGS = [
    "Hello there! I'm your friendly voice assistant.",
    "Hi! Ready to chat whenever you are.",
    "Hey! Let's talk—I'm all ears.",
]

_RESPONSES = [
    "I heard you loud and clear.",
    "That's interesting! Tell me more.",
    "Thanks for sharing that with me.",
]


@dataclass
class AssistantTurn:
    """Represents a conversational turn processed by the assistant."""

    utterance: str
    response_text: str
    audio_chunks: Iterable[bytes]


@dataclass
class ConversationState:
    """Tracks the rolling state for a single WebSocket session."""

    user_buffer: bytearray = field(default_factory=bytearray)
    turns: list[AssistantTurn] = field(default_factory=list)
    chunks_received: int = 0


class MockAssistant:
    """A tiny assistant that turns audio into cheerful placeholder replies."""

    def __init__(self) -> None:
        self._rand = random.Random()

    def _simple_transcript(self) -> str:
        """Create a pseudo-transcript for demonstration purposes."""
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"You spoke to me at {now}."

    def _build_reply(self) -> str:
        greeting = self._rand.choice(_GREETINGS)
        followup = self._rand.choice(_RESPONSES)
        return f"{greeting} {followup}"

    def handle_interaction(self, message: str) -> Dict[str, str]:
        """Return a deterministic text reply for the REST endpoint."""
        summary = self._simple_transcript()
        response = self._build_reply()
        return {
            "summary": summary,
            "reply": response,
            "echo": message,
        }

    def on_audio_chunk(self, state: ConversationState, payload: bytes) -> Optional[AssistantTurn]:
        """Handle raw audio streamed from the client and craft a reply periodically."""
        state.user_buffer.extend(payload)
        state.chunks_received += 1

        # After a few chunks, craft a response to simulate processing.
        if state.chunks_received < 3:
            return None

        transcript = self._simple_transcript()
        response_text = self._build_reply()

        # Create a few audio chunks as placeholder TTS output.
        audio_segments = [
            generate_tone_wav(320, frequency=440.0 + 30 * idx, volume=0.28)
            for idx in range(3)
        ]

        turn = AssistantTurn(
            utterance=transcript,
            response_text=response_text,
            audio_chunks=audio_segments,
        )

        state.turns.append(turn)
        state.user_buffer.clear()
        state.chunks_received = 0
        return turn

    def format_turn(self, turn: AssistantTurn) -> Dict[str, str]:
        """Serialize a conversational turn for WebSocket transport."""
        return {
            "transcript": turn.utterance,
            "response": turn.response_text,
        }

    def system_prompt(self) -> Dict[str, str]:
        """Return a welcome message when the session starts."""
        return {
            "type": "assistant_message",
            "text": self._rand.choice(_GREETINGS),
        }

    @staticmethod
    def serialize_turn(turn: AssistantTurn) -> Dict[str, str]:
        return {
            "transcript": turn.utterance,
            "response": turn.response_text,
        }

    @staticmethod
    def audio_payload(chunk: bytes) -> Dict[str, str]:
        import base64

        encoded = base64.b64encode(chunk).decode("utf-8")
        return {
            "type": "assistant_audio",
            "audio": encoded,
            "format": "audio/wav",
        }


def parse_audio_payload(message: Dict[str, str]) -> bytes:
    import base64

    payload = message.get("audio")
    if not payload:
        raise ValueError("Missing audio payload")
    return base64.b64decode(payload)
