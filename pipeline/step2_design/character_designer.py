"""Character design using Stability AI / Stable Diffusion."""
from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import List

import requests

from pipeline.models import Character, Scene
from pipeline.step2_design.lora_manager import LoRAManager
from utils.logger import get_logger

logger = get_logger(__name__)

ImagePath = Path

_STABILITY_API_URL = "https://api.stability.ai/v1/generation/{engine}/text-to-image"
_DEFAULT_ENGINE = "stable-diffusion-xl-1024-v1-0"


class CharacterDesigner:
    """Generate character reference sheets and in-scene character images.

    Args:
        provider: Image generation backend (``"stability"`` supported).
        style: Visual style descriptor injected into prompts.
        width: Output image width in pixels.
        height: Output image height in pixels.
    """

    def __init__(
        self,
        provider: str = "stability",
        style: str = "anime",
        width: int = 1920,
        height: int = 1080,
    ):
        self.provider = provider
        self.style = style
        self.width = width
        self.height = height
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.lora_manager = LoRAManager()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_character_sheet(
        self, character: Character, style: str = "anime"
    ) -> List[ImagePath]:
        """Generate a reference character sheet (multiple poses/angles).

        Args:
            character: Character model containing visual description.
            style: Override style for this generation.

        Returns:
            List of :class:`~pathlib.Path` objects pointing to saved images.
        """
        poses = ["full body front view", "side profile", "face close-up"]
        images: List[ImagePath] = []
        for pose in poses:
            prompt = self._build_character_prompt(character, style) + f", {pose}"
            output_path = Path(tempfile.mkdtemp()) / f"{character.name}_{pose.replace(' ', '_')}.png"
            try:
                img_path = self._call_stability_api(prompt, output_path)
                images.append(img_path)
            except Exception as exc:
                logger.warning(f"Character sheet generation failed for '{character.name}' ({pose}): {exc}")
        return images

    def generate_character_in_scene(
        self, character: Character, scene: Scene
    ) -> ImagePath:
        """Generate an image of a character placed within a specific scene.

        Args:
            character: Character to render.
            scene: Scene providing location and mood context.

        Returns:
            :class:`~pathlib.Path` to the generated image.
        """
        base_prompt = self._build_character_prompt(character, self.style)
        scene_context = (
            f"{scene.setting}, {scene.mood} atmosphere, "
            f"{scene.visual_notes}"
        )
        prompt = f"{base_prompt}, in scene: {scene_context}"
        output_path = (
            Path(tempfile.mkdtemp())
            / f"{character.name}_scene_{scene.scene_number}.png"
        )
        return self._call_stability_api(prompt, output_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_character_prompt(self, character: Character, style: str) -> str:
        """Compose a text-to-image prompt for a character.

        Args:
            character: Source character data.
            style: Visual style to apply.

        Returns:
            Prompt string.
        """
        lora = self.lora_manager.get_lora_prompt(character.name) or ""
        prompt_parts = [
            f"{style} style",
            character.appearance,
            f"personality: {character.personality}",
            "high quality illustration",
            "detailed",
            "cinematic lighting",
        ]
        if lora:
            prompt_parts.insert(0, lora)
        return ", ".join(p for p in prompt_parts if p)

    def _call_stability_api(self, prompt: str, output_path: Path) -> ImagePath:
        """Call the Stability AI text-to-image endpoint and save the result.

        Falls back to a placeholder PNG when no API key is configured.

        Args:
            prompt: Text prompt for image generation.
            output_path: Destination file path.

        Returns:
            Path to the saved image file.

        Raises:
            RuntimeError: If the API returns a non-200 status.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            logger.warning("STABILITY_API_KEY not set — writing placeholder image")
            _write_placeholder(output_path, self.width, self.height)
            return output_path

        engine = _DEFAULT_ENGINE
        url = _STABILITY_API_URL.format(engine=engine)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Stability API requires dimensions that are multiples of 64
        w = _round_to_64(self.width)
        h = _round_to_64(self.height)
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "height": h,
            "width": w,
            "samples": 1,
            "steps": 30,
        }
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        if response.status_code != 200:
            raise RuntimeError(
                f"Stability API error {response.status_code}: {response.text[:300]}"
            )
        result = response.json()
        image_b64 = result["artifacts"][0]["base64"]
        output_path.write_bytes(base64.b64decode(image_b64))
        logger.info(f"Saved character image: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _round_to_64(value: int) -> int:
    """Round *value* down to the nearest multiple of 64 (min 512)."""
    rounded = (value // 64) * 64
    return max(rounded, 512)


def _write_placeholder(path: Path, width: int, height: int) -> None:
    """Write a simple grey placeholder PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (min(width, 1024), min(height, 1024)), color=(180, 180, 200))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, img.width - 10, img.height - 10], outline=(100, 100, 140), width=3)
        draw.text((img.width // 2 - 60, img.height // 2), "[ placeholder ]", fill=(80, 80, 100))
        img.save(path, format="PNG")
    except Exception as exc:
        logger.warning(f"Could not write placeholder image: {exc}")
        path.write_bytes(b"")
