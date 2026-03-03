"""FFmpeg-based video compositing — merging video clips with audio and subtitles."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import ffmpeg

from utils.logger import get_logger

logger = get_logger(__name__)

VideoPath = Path
AudioPath = Path


@dataclass
class SubtitleEntry:
    """A timed subtitle entry for a scene."""

    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None


class VideoEditor:
    """Compose scene videos with dialogue audio and burned-in subtitles.

    Args:
        fps: Frames per second for output video.
        resolution: Output resolution string ``"WxH"``.
    """

    def __init__(self, fps: int = 24, resolution: str = "1920x1080"):
        self.fps = fps
        self.resolution = resolution
        width, height = resolution.split("x")
        self.width = int(width)
        self.height = int(height)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def compose_scene_video(
        self,
        video_clip: VideoPath,
        audio_clips: List[AudioPath],
        subtitles: List[SubtitleEntry],
    ) -> VideoPath:
        """Merge a video clip with audio tracks and optional subtitles.

        Audio clips are concatenated sequentially and mixed onto the video.
        Subtitles are written to a temp SRT file and burned in via a
        ``subtitles`` ffmpeg filter when at least one entry is provided.

        Args:
            video_clip: Source video file.
            audio_clips: Zero or more audio files to overlay.
            subtitles: Subtitle entries to burn into the video.

        Returns:
            Path to the composed output video.
        """
        output_path = Path(tempfile.mkdtemp()) / f"composed_{video_clip.stem}.mp4"

        try:
            video_stream = ffmpeg.input(str(video_clip))
            video_node = video_stream.video

            if audio_clips:
                # Concatenate dialogue audio clips
                audio_nodes = [ffmpeg.input(str(a)).audio for a in audio_clips]
                if len(audio_nodes) == 1:
                    audio_node = audio_nodes[0]
                else:
                    audio_node = ffmpeg.concat(*audio_nodes, v=0, a=1).audio

                if subtitles:
                    srt_path = _write_srt(subtitles)
                    video_node = video_node.filter("subtitles", str(srt_path))

                out = ffmpeg.output(
                    video_node,
                    audio_node,
                    str(output_path),
                    vcodec="libx264",
                    acodec="aac",
                    r=self.fps,
                    shortest=None,
                )
            else:
                if subtitles:
                    srt_path = _write_srt(subtitles)
                    video_node = video_node.filter("subtitles", str(srt_path))

                out = ffmpeg.output(
                    video_node,
                    str(output_path),
                    vcodec="libx264",
                    r=self.fps,
                )

            ffmpeg.run(out, overwrite_output=True, quiet=True)
            logger.info(f"Composed scene video: {output_path}")
        except ffmpeg.Error as exc:
            logger.warning(f"ffmpeg compose failed: {exc} — copying source as fallback")
            import shutil
            shutil.copy2(video_clip, output_path)

        return output_path

    def add_transitions(
        self,
        clips: List[VideoPath],
        transition_type: str = "crossfade",
        duration: float = 0.5,
    ) -> VideoPath:
        """Concatenate clips with transition effects between them.

        Uses the ``xfade`` ffmpeg filter for crossfade transitions, or simple
        concatenation for unsupported transition types.

        Args:
            clips: Ordered list of video clip paths.
            transition_type: Transition style (``"crossfade"`` or ``"cut"``).
            duration: Transition overlap duration in seconds.

        Returns:
            Path to the concatenated output video.
        """
        output_path = Path(tempfile.mkdtemp()) / "with_transitions.mp4"

        if not clips:
            raise ValueError("No clips provided to add_transitions")

        try:
            if len(clips) == 1 or transition_type.lower() == "cut":
                _concat_clips(clips, output_path, self.fps)
            else:
                _xfade_clips(clips, output_path, duration, self.fps)
        except Exception as exc:
            logger.warning(f"Transition processing failed: {exc} — falling back to cut concat")
            _concat_clips(clips, output_path, self.fps)

        logger.info(f"Added transitions ({transition_type}): {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _write_srt(subtitles: List[SubtitleEntry]) -> Path:
    """Write subtitle entries to a temporary SRT file."""
    srt_path = Path(tempfile.mkdtemp()) / "subtitles.srt"
    lines: List[str] = []
    for idx, sub in enumerate(subtitles, start=1):
        speaker_prefix = f"[{sub.speaker}] " if sub.speaker else ""
        lines.append(
            f"{idx}\n"
            f"{_fmt_srt_time(sub.start_time)} --> {_fmt_srt_time(sub.end_time)}\n"
            f"{speaker_prefix}{sub.text}\n"
        )
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return srt_path


def _fmt_srt_time(seconds: float) -> str:
    """Format seconds as ``HH:MM:SS,mmm`` for SRT files."""
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    s = (total_ms // 1000) % 60
    m = (total_ms // 60_000) % 60
    h = total_ms // 3_600_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _concat_clips(clips: List[VideoPath], output_path: Path, fps: int) -> None:
    """Simple ffmpeg concat demuxer concatenation."""
    list_file = Path(tempfile.mkdtemp()) / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{c.resolve()}'" for c in clips), encoding="utf-8"
    )
    (
        ffmpeg
        .input(str(list_file), format="concat", safe=0)
        .output(str(output_path), vcodec="libx264", acodec="aac", r=fps)
        .run(overwrite_output=True, quiet=True)
    )


def _xfade_clips(
    clips: List[VideoPath],
    output_path: Path,
    duration: float,
    fps: int,
) -> None:
    """Chain xfade filters between consecutive clips."""
    # Probe durations
    inputs = [ffmpeg.input(str(c)) for c in clips]
    current_video = inputs[0].video
    current_audio = inputs[0].audio

    offset = 0.0
    for i in range(1, len(inputs)):
        # Probe previous clip duration for offset calculation
        try:
            probe = ffmpeg.probe(str(clips[i - 1]))
            clip_dur = float(probe["format"]["duration"])
        except Exception:
            clip_dur = 5.0
        offset += clip_dur - duration

        current_video = ffmpeg.filter(
            [current_video, inputs[i].video],
            "xfade",
            transition="fade",
            duration=duration,
            offset=max(offset, 0),
        )
        current_audio = ffmpeg.filter(
            [current_audio, inputs[i].audio],
            "acrossfade",
            d=duration,
        )

    (
        ffmpeg
        .output(current_video, current_audio, str(output_path), vcodec="libx264", acodec="aac", r=fps)
        .run(overwrite_output=True, quiet=True)
    )
