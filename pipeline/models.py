"""Shared Pydantic data models for the Anime Creation Pipeline."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class DialogueLine(BaseModel):
    """A single line of dialogue spoken by a character."""

    character: str
    text: str
    emotion: Optional[str] = None


class Character(BaseModel):
    """A character in the anime story."""

    name: str
    description: str
    personality: str
    appearance: str


class Scene(BaseModel):
    """A single scene in the anime script."""

    scene_number: int
    setting: str
    description: str
    dialogue: List[DialogueLine] = []
    visual_notes: str = ""
    mood: str = ""


class Script(BaseModel):
    """A complete anime script produced by the story generator."""

    title: str
    synopsis: str
    characters: List[Character] = []
    scenes: List[Scene] = []
