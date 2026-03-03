"""Audio mixing utilities using FFmpeg."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

import ffmpeg

from utils.logger import get_logger

logger = get_logger(__name__)

AudioPath = Path


class AudioMixer:
    """Mix dialogue, background music and sound effects into a single track."""

    def mix_audio(
        self,
        dialogue: List[AudioPath],
        bgm: Optional[AudioPath] = None,
        sfx: Optional[List[AudioPath]] = None,
    ) -> AudioPath:
        """Mix dialogue, optional BGM and optional SFX into one audio file.

        Dialogue clips are concatenated first, then all streams are merged with
        ``amix``.  BGM is attenuated to −12 dB so dialogue remains clear.

        Args:
            dialogue: Ordered list of dialogue audio clips.
            bgm: Optional background music track.
            sfx: Optional list of sound-effect clips (overlaid at −6 dB).

        Returns:
            Path to the mixed audio file (AAC, 44.1 kHz).
        """
        output_path = Path(tempfile.mkdtemp()) / "mixed_audio.aac"

        if not dialogue and not bgm:
            logger.warning("No audio sources provided — writing silence placeholder")
            _write_silent_wav(output_path.with_suffix(".wav"))
            return output_path.with_suffix(".wav")

        try:
            streams: List = []

            # Concatenate dialogue clips
            if dialogue:
                if len(dialogue) == 1:
                    dialogue_node = ffmpeg.input(str(dialogue[0])).audio
                else:
                    parts = [ffmpeg.input(str(d)).audio for d in dialogue]
                    dialogue_node = ffmpeg.concat(*parts, v=0, a=1).audio
                streams.append(dialogue_node)

            # BGM: lower volume
            if bgm and bgm.exists():
                bgm_node = ffmpeg.input(str(bgm)).audio.filter("volume", "0.25")
                streams.append(bgm_node)

            # SFX: slightly lower volume
            sfx = sfx or []
            for sfx_path in sfx:
                if sfx_path.exists():
                    sfx_node = ffmpeg.input(str(sfx_path)).audio.filter("volume", "0.5")
                    streams.append(sfx_node)

            if len(streams) == 1:
                mixed = streams[0]
            else:
                mixed = ffmpeg.filter(streams, "amix", inputs=len(streams), normalize=0)

            ffmpeg.output(mixed, str(output_path), acodec="aac", ar=44100).run(
                overwrite_output=True, quiet=True
            )
            logger.info(f"Mixed audio: {output_path}")
        except ffmpeg.Error as exc:
            logger.warning(f"ffmpeg audio mix failed: {exc} — using first dialogue track")
            if dialogue and dialogue[0].exists():
                import shutil
                shutil.copy2(dialogue[0], output_path)
            else:
                _write_silent_wav(output_path.with_suffix(".wav"))
                return output_path.with_suffix(".wav")

        return output_path

    def normalize_audio(self, audio: AudioPath) -> AudioPath:
        """Normalise audio loudness to −16 LUFS (broadcast standard).

        Uses the ``loudnorm`` ffmpeg filter for EBU R128 normalisation.

        Args:
            audio: Source audio file.

        Returns:
            Path to the normalised audio file.
        """
        output_path = audio.parent / f"norm_{audio.name}"
        try:
            (
                ffmpeg
                .input(str(audio))
                .audio
                .filter("loudnorm", I=-16, TP=-1.5, LRA=11)
                .output(str(output_path), acodec="aac", ar=44100)
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Normalised audio: {output_path}")
        except ffmpeg.Error as exc:
            logger.warning(f"Audio normalisation failed: {exc} — returning original")
            return audio
        return output_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_silent_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 44100) -> None:
    """Write a minimal silent WAV file."""
    import struct
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    n_samples = int(sample_rate * duration_s)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
