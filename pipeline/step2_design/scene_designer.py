"""Scene/background generation using Stability AI / Stable Diffusion."""
from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import List

import requests

from pipeline.models import Scene
from utils.logger import get_logger

logger = get_logger(__name__)

ImagePath = Path

_STABILITY_API_URL = "https://api.stability.ai/v1/generation/{engine}/text-to-image"
_DEFAULT_ENGINE = "stable-diffusion-xl-1024-v1-0"


class SceneDesigner:
    """Generate backgrounds and composite scene images.

    Args:
        provider: Image generation backend (``"stability"`` supported).
        style: Visual style descriptor.
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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_background(self, scene: Scene, style: str = "anime") -> ImagePath:
        """Generate a background image for a scene.

        Args:
            scene: Scene model providing setting, mood and visual notes.
            style: Override style for this generation.

        Returns:
            :class:`~pathlib.Path` to the saved background image.
        """
        prompt = self._build_scene_prompt(scene, style)
        output_path = (
            Path(tempfile.mkdtemp()) / f"bg_scene_{scene.scene_number}.png"
        )
        return self._call_stability_api(prompt, output_path)

    def compose_scene(
        self, characters: List[ImagePath], background: ImagePath
    ) -> ImagePath:
        """Composite character images onto a background.

        Uses Pillow to paste each character image onto the background at evenly
        spaced positions.

        Args:
            characters: List of character image paths.
            background: Background image path.

        Returns:
            Path to the composited image.
        """
        from PIL import Image

        try:
            bg = Image.open(background).convert("RGBA")
        except Exception as exc:
            logger.warning(f"Could not open background {background}: {exc}")
            bg = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))

        n = len(characters)
        for i, char_path in enumerate(characters):
            try:
                char_img = Image.open(char_path).convert("RGBA")
                # Scale character to ~40 % of bg height
                target_h = int(bg.height * 0.4)
                scale = target_h / char_img.height
                new_size = (int(char_img.width * scale), target_h)
                char_img = char_img.resize(new_size, Image.LANCZOS)
                # Distribute horizontally
                x = int(bg.width * (i + 1) / (n + 1)) - new_size[0] // 2
                y = bg.height - new_size[1] - 20
                bg.paste(char_img, (x, y), char_img)
            except Exception as exc:
                logger.warning(f"Could not composite character {char_path}: {exc}")

        output_path = background.parent / f"composed_{background.name}"
        bg.convert("RGB").save(output_path, format="PNG")
        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_scene_prompt(self, scene: Scene, style: str) -> str:
        """Compose a text-to-image prompt for a scene background.

        Args:
            scene: Scene source data.
            style: Visual style descriptor.

        Returns:
            Prompt string.
        """
        parts = [
            f"{style} style background",
            f"location: {scene.setting}",
            f"{scene.mood} atmosphere" if scene.mood else "",
            scene.visual_notes,
            "no characters",
            "highly detailed",
            "cinematic composition",
            "4k quality",
        ]
        return ", ".join(p for p in parts if p)

    def _call_stability_api(self, prompt: str, output_path: Path) -> ImagePath:
        """Call the Stability AI text-to-image endpoint and save the result.

        Falls back to a placeholder when no API key is configured.

        Args:
            prompt: Text prompt.
            output_path: Destination file path.

        Returns:
            Path to saved image.

        Raises:
            RuntimeError: On API error.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            logger.warning("STABILITY_API_KEY not set — writing placeholder background")
            _write_placeholder(output_path, self.width, self.height)
            return output_path

        engine = _DEFAULT_ENGINE
        url = _STABILITY_API_URL.format(engine=engine)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
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
        logger.info(f"Saved background image: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _round_to_64(value: int) -> int:
    rounded = (value // 64) * 64
    return max(rounded, 512)


def _write_placeholder(path: Path, width: int, height: int) -> None:
    try:
        from PIL import Image, ImageDraw

        w, h = min(width, 1024), min(height, 576)
        img = Image.new("RGB", (w, h), color=(30, 30, 60))
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, w - 5, h - 5], outline=(60, 60, 120), width=2)
        draw.text((w // 2 - 80, h // 2), "[ scene background ]", fill=(120, 120, 180))
        img.save(path, format="PNG")
    except Exception as exc:
        logger.warning(f"Could not write placeholder: {exc}")
        path.write_bytes(b"")
