"""Final render and export using FFmpeg."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

import ffmpeg

from utils.logger import get_logger

logger = get_logger(__name__)

VideoPath = Path

_QUALITY_PRESETS = {
    "low": {"crf": "28", "preset": "fast"},
    "medium": {"crf": "23", "preset": "medium"},
    "high": {"crf": "18", "preset": "slow"},
    "lossless": {"crf": "0", "preset": "veryslow"},
}


class FinalRenderer:
    """Assemble, encode and export the finished anime episode.

    Args:
        output_format: Container format (e.g. ``"mp4"``).
        codec: Video codec (e.g. ``"h264"``).
        fps: Output frame rate.
        resolution: Output resolution ``"WxH"``.
    """

    def __init__(
        self,
        output_format: str = "mp4",
        codec: str = "h264",
        fps: int = 24,
        resolution: str = "1920x1080",
    ):
        self.output_format = output_format
        self.codec = codec
        self.fps = fps
        self.resolution = resolution

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def render_episode(
        self,
        scene_videos: List[VideoPath],
        intro: Optional[VideoPath] = None,
        outro: Optional[VideoPath] = None,
    ) -> VideoPath:
        """Concatenate scene clips (with optional intro/outro) into one video.

        Args:
            scene_videos: Ordered list of composed scene clip paths.
            intro: Optional intro clip prepended to the episode.
            outro: Optional outro clip appended to the episode.

        Returns:
            Path to the assembled episode video.
        """
        output_path = Path(tempfile.mkdtemp()) / f"episode.{self.output_format}"

        all_clips: List[VideoPath] = []
        if intro and intro.exists():
            all_clips.append(intro)
        all_clips.extend(v for v in scene_videos if v.exists())
        if outro and outro.exists():
            all_clips.append(outro)

        if not all_clips:
            raise ValueError("No valid video clips to render")

        if len(all_clips) == 1:
            shutil.copy2(all_clips[0], output_path)
            logger.info(f"Single clip episode: {output_path}")
            return output_path

        try:
            list_file = Path(tempfile.mkdtemp()) / "episode_list.txt"
            list_file.write_text(
                "\n".join(f"file '{c.resolve()}'" for c in all_clips),
                encoding="utf-8",
            )
            width, height = self.resolution.split("x")
            vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            (
                ffmpeg
                .input(str(list_file), format="concat", safe=0)
                .output(
                    str(output_path),
                    vcodec="libx264",
                    acodec="aac",
                    r=self.fps,
                    vf=vf,
                    crf=18,
                    preset="medium",
                )
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Rendered episode: {output_path}")
        except ffmpeg.Error as exc:
            logger.warning(f"ffmpeg render failed: {exc} — copying first clip as fallback")
            shutil.copy2(all_clips[0], output_path)

        return output_path

    def export(
        self,
        video: VideoPath,
        format: str = "mp4",
        quality: str = "high",
    ) -> VideoPath:
        """Re-encode and export *video* with the specified quality preset.

        Args:
            video: Source video to export.
            format: Output container format (e.g. ``"mp4"``, ``"webm"``).
            quality: Quality preset key from :data:`_QUALITY_PRESETS`.

        Returns:
            Path to the exported file placed alongside *video*.
        """
        preset = _QUALITY_PRESETS.get(quality, _QUALITY_PRESETS["high"])
        output_path = video.parent / f"final_export.{format}"

        codec_map = {
            "mp4": "libx264",
            "webm": "libvpx-vp9",
            "mkv": "libx264",
            "mov": "libx264",
        }
        vcodec = codec_map.get(format, "libx264")

        try:
            width, height = self.resolution.split("x")
            vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
            (
                ffmpeg
                .input(str(video))
                .output(
                    str(output_path),
                    vcodec=vcodec,
                    acodec="aac",
                    r=self.fps,
                    vf=vf,
                    crf=preset["crf"],
                    preset=preset["preset"],
                )
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Exported: {output_path} (quality={quality})")
        except ffmpeg.Error as exc:
            logger.warning(f"Export encode failed: {exc} — copying source")
            shutil.copy2(video, output_path)

        return output_path
