"""Shared data models."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class FieldStatus(str, Enum):
    present = "present"
    missing = "missing"
    found_internal = "found_internal"
    found_external = "found_external"


class InfoItem(BaseModel):
    """A required field on the referral letter and its state (used by mock_data detection)."""

    name: str
    category: str  # "administrative" | "clinical"
    status: FieldStatus
    value: str | None = None
    source: str | None = None
    context: str | None = None


class Event(BaseModel):
    """A single streamed step, rendered live in the UI."""

    kind: str  # "plan" | "agent_start" | "thought" | "agent_done" | "final"
    step: int = 0
    agent: str = ""
    text: str = ""
    data: dict | None = None
