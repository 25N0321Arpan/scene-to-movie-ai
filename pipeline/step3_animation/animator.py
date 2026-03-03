"""Animation using Pika / Runway / local OpenCV fallback."""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests

from pipeline.models import Scene
from utils.logger import get_logger

logger = get_logger(__name__)

ImagePath = Path
VideoPath = Path


@dataclass
class SceneAssets:
    """Bundles a scene with its source image and motion prompt."""

    scene: Scene
    image: ImagePath
    motion_prompt: str


class Animator:
    """Animate static images into short video clips.

    Supports Pika Labs, Runway Gen-2, and a local OpenCV pan/zoom fallback.

    Args:
        provider: ``"pika"``, ``"runway"``, or ``"local"``.
        duration_per_scene: Target clip duration in seconds.
        fps: Frames per second for local rendering.
    """

    def __init__(
        self,
        provider: str = "pika",
        duration_per_scene: float = 5.0,
        fps: int = 24,
    ):
        self.provider = provider
        self.duration = duration_per_scene
        self.fps = fps

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def animate_scene(
        self,
        image: ImagePath,
        motion_prompt: str,
        duration: float,
    ) -> VideoPath:
        """Animate a single image into a video clip.

        Args:
            image: Path to the source image.
            motion_prompt: Textual description of desired motion.
            duration: Desired clip length in seconds.

        Returns:
            :class:`~pathlib.Path` to the generated video file.
        """
        provider = self.provider.lower()
        if provider == "pika":
            return self._animate_pika(image, motion_prompt, duration)
        elif provider == "runway":
            return self._animate_runway(image, motion_prompt, duration)
        else:
            output_path = Path(tempfile.mkdtemp()) / f"{image.stem}_animated.mp4"
            return self._animate_local(image, motion_prompt, duration, output_path)

    def batch_animate(self, scenes: List[SceneAssets]) -> List[VideoPath]:
        """Animate a batch of scene assets sequentially.

        Args:
            scenes: List of :class:`SceneAssets` to process.

        Returns:
            List of :class:`~pathlib.Path` objects pointing to generated clips.
        """
        results: List[VideoPath] = []
        for i, asset in enumerate(scenes, start=1):
            logger.info(f"  Animating scene {i}/{len(scenes)}: {asset.scene.setting}")
            try:
                clip = self.animate_scene(asset.image, asset.motion_prompt, self.duration)
                results.append(clip)
            except Exception as exc:
                logger.warning(f"  Animation failed for scene {i}: {exc} — using fallback")
                fallback = Path(tempfile.mkdtemp()) / f"scene_{i}_fallback.mp4"
                clip = self._animate_local(asset.image, asset.motion_prompt, self.duration, fallback)
                results.append(clip)
        return results

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _animate_local(
        self,
        image: ImagePath,
        motion_prompt: str,
        duration: float,
        output_path: Path,
    ) -> VideoPath:
        """Local fallback: create a pan/zoom video from a static image using OpenCV.

        Applies a slow Ken Burns–style zoom-in effect.

        Args:
            image: Source image path.
            motion_prompt: Unused (kept for API consistency).
            duration: Desired video duration in seconds.
            output_path: Destination MP4 file path.

        Returns:
            Path to the generated MP4 file.
        """
        import cv2
        import numpy as np

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Read source image
        try:
            img = cv2.imread(str(image))
            if img is None:
                raise ValueError(f"cv2 could not read image: {image}")
        except Exception:
            # Create a dark placeholder frame
            img = np.zeros((576, 1024, 3), dtype=np.uint8)
            img[:] = (30, 30, 60)

        orig_h, orig_w = img.shape[:2]
        out_w, out_h = 1280, 720
        total_frames = int(duration * self.fps)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, float(self.fps), (out_w, out_h))

        for frame_idx in range(total_frames):
            t = frame_idx / max(total_frames - 1, 1)  # 0.0 → 1.0
            # Zoom from 1.0x to 1.1x (subtle Ken Burns)
            zoom = 1.0 + 0.1 * t
            crop_w = int(orig_w / zoom)
            crop_h = int(orig_h / zoom)
            # Centre crop
            x0 = (orig_w - crop_w) // 2
            y0 = (orig_h - crop_h) // 2
            cropped = img[y0 : y0 + crop_h, x0 : x0 + crop_w]
            frame = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
            writer.write(frame)

        writer.release()
        logger.info(f"Local animation saved: {output_path} ({total_frames} frames @ {self.fps} fps)")
        return output_path

    def _animate_pika(
        self,
        image: ImagePath,
        motion_prompt: str,
        duration: float,
    ) -> VideoPath:
        """Animate via the Pika Labs API (image-to-video).

        Args:
            image: Source image path.
            motion_prompt: Motion description.
            duration: Target duration in seconds.

        Returns:
            Path to the downloaded video file.

        Raises:
            RuntimeError: If the API key is missing or the request fails.
        """
        api_key = os.getenv("PIKA_API_KEY")
        if not api_key:
            logger.warning("PIKA_API_KEY not set — falling back to local animation")
            output_path = Path(tempfile.mkdtemp()) / f"{image.stem}_pika.mp4"
            return self._animate_local(image, motion_prompt, duration, output_path)

        upload_url = "https://api.pika.art/generate"
        with open(image, "rb") as f:
            files = {"image": (image.name, f, "image/png")}
            data = {
                "promptText": motion_prompt,
                "duration": int(duration),
                "frameRate": self.fps,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.post(upload_url, files=files, data=data, headers=headers, timeout=180)

        if response.status_code != 200:
            raise RuntimeError(f"Pika API error {response.status_code}: {response.text[:200]}")

        result = response.json()
        video_url = result.get("video_url") or result.get("url")
        if not video_url:
            raise RuntimeError(f"Pika API returned no video URL: {result}")

        output_path = Path(tempfile.mkdtemp()) / f"{image.stem}_pika.mp4"
        self._download_video(video_url, output_path)
        return output_path

    def _animate_runway(
        self,
        image: ImagePath,
        motion_prompt: str,
        duration: float,
    ) -> VideoPath:
        """Animate via the Runway Gen-2 API (image-to-video).

        Args:
            image: Source image path.
            motion_prompt: Motion description.
            duration: Target duration in seconds.

        Returns:
            Path to the downloaded video file.

        Raises:
            RuntimeError: If the API key is missing or the request fails.
        """
        api_key = os.getenv("RUNWAY_API_KEY")
        if not api_key:
            logger.warning("RUNWAY_API_KEY not set — falling back to local animation")
            output_path = Path(tempfile.mkdtemp()) / f"{image.stem}_runway.mp4"
            return self._animate_local(image, motion_prompt, duration, output_path)

        import base64

        with open(image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "image": f"data:image/png;base64,{image_b64}",
            "prompt": motion_prompt,
            "duration": int(duration),
            "ratio": "1280:720",
        }
        response = requests.post(
            "https://api.runwayml.com/v1/image_to_video",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in (200, 201, 202):
            raise RuntimeError(f"Runway API error {response.status_code}: {response.text[:200]}")

        result = response.json()
        task_id = result.get("id")
        if not task_id:
            raise RuntimeError(f"Runway did not return a task id: {result}")

        # Poll for completion
        video_url = self._poll_runway_task(task_id, headers)
        output_path = Path(tempfile.mkdtemp()) / f"{image.stem}_runway.mp4"
        self._download_video(video_url, output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_runway_task(self, task_id: str, headers: dict, max_wait: int = 300) -> str:
        """Poll the Runway task endpoint until the video is ready.

        Args:
            task_id: Runway generation task identifier.
            headers: Auth headers for API calls.
            max_wait: Maximum wait time in seconds.

        Returns:
            Video download URL.

        Raises:
            RuntimeError: If polling times out or the task fails.
        """
        poll_url = f"https://api.runwayml.com/v1/tasks/{task_id}"
        elapsed = 0
        interval = 5
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            resp = requests.get(poll_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"Runway polling error {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            status = data.get("status", "")
            if status == "SUCCEEDED":
                url = data.get("output", [None])[0]
                if not url:
                    raise RuntimeError("Runway task succeeded but no output URL found")
                return url
            elif status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"Runway task {status}: {data.get('failure', '')}")
            logger.debug(f"  Runway task {task_id} status={status}, waiting…")
        raise RuntimeError(f"Runway task {task_id} did not complete within {max_wait}s")

    @staticmethod
    def _download_video(url: str, output_path: Path) -> None:
        """Stream-download a video URL to a local file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Downloaded video: {output_path}")
