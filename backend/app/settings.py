"""Configuration helpers for Azure Voice Live integration."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential


DEFAULT_INSTRUCTIONS = (
    "You are a helpful AI assistant with access to functions. "
    "Use the functions when appropriate to provide accurate, real-time information. "
    "If you are asked about the weather, please respond with 'I will get the weather for you. Please wait a moment.' "
    "and then call the get_current_weather function. "
    "If you are asked about the time, please respond with 'I will get the time for you. Please wait a moment.' "
    "and then call the get_current_time function. Explain when you're using a function and include the results in your response naturally."
)


@dataclass
class VoiceLiveSettings:
    """Runtime configuration for Azure Voice Live streaming."""

    endpoint: str
    model: str
    voice: str
    instructions: str
    show_transcriptions: bool
    input_audio_format: str = "pcm16"
    sample_rate_hz: int = 24000
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "VoiceLiveSettings":
        endpoint = os.getenv("AZURE_VOICELIVE_ENDPOINT", "wss://api.voicelive.com/v1")
        model = os.getenv("AZURE_VOICELIVE_MODEL", "gpt-4o-realtime-preview")
        voice = os.getenv("AZURE_VOICELIVE_VOICE", "en-US-AvaNeural")
        instructions = os.getenv("AZURE_VOICELIVE_INSTRUCTIONS", DEFAULT_INSTRUCTIONS)
        show_transcriptions = os.getenv("AZURE_VOICELIVE_SHOW_TRANSCRIPTIONS", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        api_key = os.getenv("AZURE_VOICELIVE_API_KEY")

        return cls(
            endpoint=endpoint,
            model=model,
            voice=voice,
            instructions=instructions,
            show_transcriptions=show_transcriptions,
            api_key=api_key,
        )

    @asynccontextmanager
    async def credential_context(self) -> AsyncIterator[AzureKeyCredential | AsyncTokenCredential]:
        """Yield a credential instance suitable for the Voice Live SDK."""

        if self.api_key:
            yield AzureKeyCredential(self.api_key)
            return

        credential = DefaultAzureCredential()
        try:
            yield credential
        finally:
            await credential.close()
