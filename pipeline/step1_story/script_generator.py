"""Script generation using LLM backends (OpenAI / Anthropic)."""
from __future__ import annotations

import json
import os
from typing import Optional

import anthropic
import openai

from pipeline.models import Character, DialogueLine, Scene, Script
from pipeline.step1_story.prompts import (
    ANIME_SCRIPT_SYSTEM_PROMPT,
    ANIME_SCRIPT_USER_PROMPT,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    """Generates and refines anime scripts via a configurable LLM provider.

    Args:
        provider: ``"openai"`` or ``"anthropic"``.
        model: Model identifier (e.g. ``"gpt-4"`` or ``"claude-3-opus-20240229"``).
        temperature: Sampling temperature for the LLM.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        temperature: float = 0.8,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature

        if provider == "openai":
            self.client: openai.OpenAI | anthropic.Anthropic = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
        elif provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        else:
            raise ValueError(f"Unknown provider: {provider!r}. Choose 'openai' or 'anthropic'.")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def generate_script(
        self,
        prompt: str,
        num_scenes: int = 5,
        style: str = "anime",
    ) -> Script:
        """Generate a structured anime script from a high-level story idea.

        Args:
            prompt: High-level story premise.
            num_scenes: Target number of scenes.
            style: Visual style descriptor (e.g. ``"anime"``, ``"shonen"``).

        Returns:
            A populated :class:`~pipeline.models.Script` instance.
        """
        user_prompt = ANIME_SCRIPT_USER_PROMPT.format(
            prompt=prompt,
            num_scenes=num_scenes,
            style=style,
        )
        logger.debug(f"Calling {self.provider}/{self.model} for script generation")
        raw = self._call_llm(ANIME_SCRIPT_SYSTEM_PROMPT, user_prompt)
        script = self._parse_script_response(raw)
        logger.info(
            f"Generated script '{script.title}' with {len(script.scenes)} scenes "
            f"and {len(script.characters)} characters"
        )
        return script

    def refine_script(self, script: Script, feedback: str) -> Script:
        """Iteratively refine a script based on feedback.

        Args:
            script: The existing :class:`~pipeline.models.Script` to improve.
            feedback: Human-readable improvement notes.

        Returns:
            A refined :class:`~pipeline.models.Script`.
        """
        system = (
            ANIME_SCRIPT_SYSTEM_PROMPT
            + "\nYou are refining an existing script. Apply the requested changes "
            "while preserving the overall structure."
        )
        user = (
            f"Refine the following anime script based on this feedback:\n\n"
            f"FEEDBACK:\n{feedback}\n\n"
            f"CURRENT SCRIPT (JSON):\n{script.model_dump_json(indent=2)}\n\n"
            "Return the complete updated script as JSON using the same schema."
        )
        raw = self._call_llm(system, user)
        refined = self._parse_script_response(raw)
        logger.info(f"Refined script '{refined.title}'")
        return refined

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_llm(self, system: str, user: str) -> str:
        """Call the configured LLM and return the raw text response.

        Args:
            system: System prompt string.
            user: User prompt string.

        Returns:
            Raw text content from the model.

        Raises:
            RuntimeError: If the API call fails or returns empty content.
        """
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(  # type: ignore[union-attr]
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                content = response.choices[0].message.content or ""
                return content.strip()

            elif self.provider == "anthropic":
                response = self.client.messages.create(  # type: ignore[union-attr]
                    model=self.model,
                    max_tokens=4096,
                    temperature=self.temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                content = response.content[0].text if response.content else ""
                return content.strip()

        except Exception as exc:
            raise RuntimeError(f"LLM call failed ({self.provider}): {exc}") from exc

        return ""

    def _parse_script_response(self, response: str) -> Script:
        """Parse the LLM JSON response into a :class:`~pipeline.models.Script`.

        Strips optional markdown code fences before parsing.

        Args:
            response: Raw string returned by :meth:`_call_llm`.

        Returns:
            A :class:`~pipeline.models.Script` instance.

        Raises:
            ValueError: If the response cannot be parsed as valid script JSON.
        """
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON: {exc}\n--- raw ---\n{response[:500]}"
            ) from exc

        # Normalise characters
        characters: List[Character] = []
        for c in data.get("characters", []):
            characters.append(
                Character(
                    name=c.get("name", "Unknown"),
                    description=c.get("description", ""),
                    personality=c.get("personality", ""),
                    appearance=c.get("appearance", ""),
                )
            )

        # Normalise scenes
        scenes: List[Scene] = []
        for s in data.get("scenes", []):
            dialogue: List[DialogueLine] = []
            for d in s.get("dialogue", []):
                dialogue.append(
                    DialogueLine(
                        character=d.get("character", "Unknown"),
                        text=d.get("text", ""),
                        emotion=d.get("emotion"),
                    )
                )
            scenes.append(
                Scene(
                    scene_number=int(s.get("scene_number", len(scenes) + 1)),
                    setting=s.get("setting", ""),
                    description=s.get("description", ""),
                    dialogue=dialogue,
                    visual_notes=s.get("visual_notes", ""),
                    mood=s.get("mood", ""),
                )
            )

        return Script(
            title=data.get("title", "Untitled"),
            synopsis=data.get("synopsis", ""),
            characters=characters,
            scenes=scenes,
        )
