"""Pydantic schemas for HTTP endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InteractionRequest(BaseModel):
    message: str = Field(..., description="User supplied text message")


class InteractionResponse(BaseModel):
    summary: str
    reply: str
    echo: str
