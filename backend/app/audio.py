"""Utility helpers for generating placeholder audio responses."""

from __future__ import annotations

import math
import struct
from array import array
from typing import Iterable


SAMPLE_RATE = 16000
BIT_DEPTH = 16
CHANNELS = 1
_BYTES_PER_SAMPLE = BIT_DEPTH // 8


def _tone_samples(duration_ms: int, frequency: float, volume: float = 0.5) -> Iterable[int]:
    """Yield signed 16-bit samples for a sine tone."""
    total_samples = int(SAMPLE_RATE * duration_ms / 1000)
    amplitude = int(volume * ((1 << (BIT_DEPTH - 1)) - 1))
    for index in range(total_samples):
        value = int(amplitude * math.sin(2.0 * math.pi * frequency * index / SAMPLE_RATE))
        yield value


def generate_tone_wav(duration_ms: int = 600, *, frequency: float = 440.0, volume: float = 0.35) -> bytes:
    """Generate a small mono WAV tone suitable for placeholder TTS output."""
    samples = array("h", _tone_samples(duration_ms, frequency, volume))
    pcm_bytes = samples.tobytes()

    data_size = len(pcm_bytes)
    byte_rate = SAMPLE_RATE * CHANNELS * _BYTES_PER_SAMPLE
    block_align = CHANNELS * _BYTES_PER_SAMPLE

    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    fmt_chunk = b"fmt " + struct.pack(
        "<IHHIIHH",
        16,  # chunk size
        0x0001,  # PCM format
        CHANNELS,
        SAMPLE_RATE,
        byte_rate,
        block_align,
        BIT_DEPTH,
    )
    data_chunk = b"data" + struct.pack("<I", data_size)
    return header + fmt_chunk + data_chunk + pcm_bytes
