"""Voice synthesis using ElevenLabs / Edge TTS text-to-speech."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import requests

from pipeline.models import Scene
from pipeline.step4_voice.voice_profiles import VoiceProfileManager
from utils.logger import get_logger

logger = get_logger(__name__)

AudioPath = Path

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


class VoiceSynthesizer:
    """Synthesize dialogue audio using ElevenLabs or Edge TTS.

    Falls back to writing a silent placeholder WAV when no API key is set
    (ElevenLabs provider only).

    Args:
        provider: ``"elevenlabs"`` or ``"edge-tts"``.
        model: ElevenLabs model identifier (used only for ``"elevenlabs"`` provider).
    """

    def __init__(self, provider: str = "elevenlabs", model: str = "eleven_multilingual_v2"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.profile_manager = VoiceProfileManager()
        self.base_url = _ELEVENLABS_BASE

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def synthesize_line(
        self,
        text: str,
        voice_id: str,
        emotion: str = "neutral",
    ) -> AudioPath:
        """Synthesize a single line of dialogue to an audio file.

        Args:
            text: Text to speak.
            voice_id: Voice identifier (ElevenLabs voice ID or Edge TTS voice name).
            emotion: Emotion tag (used for logging).

        Returns:
            :class:`~pathlib.Path` to the synthesized audio file.
        """
        output_path = Path(tempfile.mkdtemp()) / f"tts_{abs(hash(text))}.mp3"

        if self.provider == "edge-tts":
            import edge_tts
            mp3_path = output_path.with_suffix(".mp3")

            async def _run() -> None:
                communicate = edge_tts.Communicate(text, voice_id)
                await communicate.save(str(mp3_path))

            asyncio.run(_run())
            logger.info(f"Synthesized line via Edge TTS ({emotion}): {text[:40]}… → {mp3_path.name}")
            return mp3_path

        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set — writing silent placeholder audio")
            _write_silent_wav(output_path.with_suffix(".wav"))
            return output_path.with_suffix(".wav")

        url = f"{self.base_url}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        profile = None
        # Try to find a profile that matches this voice_id for fine-grained settings
        for p in self.profile_manager.profiles.values():
            if p.voice_id == voice_id:
                profile = p
                break

        payload: Dict = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": profile.stability if profile else 0.5,
                "similarity_boost": profile.similarity_boost if profile else 0.75,
                "style": profile.style if profile else 0.0,
                "use_speaker_boost": profile.use_speaker_boost if profile else True,
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs API error {response.status_code}: {response.text[:200]}"
            )

        output_path.write_bytes(response.content)
        logger.info(f"Synthesized line ({emotion}): {text[:40]}… → {output_path.name}")
        return output_path

    def synthesize_scene_dialogue(
        self,
        scene: Scene,
        voice_map: Dict[str, str],
    ) -> List[AudioPath]:
        """Synthesize all dialogue lines in a scene.

        Args:
            scene: Scene whose ``dialogue`` list will be processed.
            voice_map: Mapping of character name → ElevenLabs voice ID.

        Returns:
            Ordered list of audio file paths corresponding to each dialogue line.
        """
        audio_paths: List[AudioPath] = []
        for i, line in enumerate(scene.dialogue):
            voice_id = voice_map.get(
                line.character,
                self.profile_manager.get_voice_id(line.character),
            )
            try:
                audio = self.synthesize_line(
                    text=line.text,
                    voice_id=voice_id,
                    emotion=line.emotion or "neutral",
                )
                audio_paths.append(audio)
            except Exception as exc:
                logger.warning(
                    f"Voice synthesis failed for line {i} in scene "
                    f"{scene.scene_number}: {exc}"
                )
                placeholder = Path(tempfile.mkdtemp()) / f"scene_{scene.scene_number}_line_{i}.wav"
                _write_silent_wav(placeholder)
                audio_paths.append(placeholder)
        return audio_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_silent_wav(path: Path, duration_s: float = 2.0, sample_rate: int = 22050) -> None:
    """Write a silent WAV file to *path*.

    Args:
        path: Destination path.
        duration_s: Duration of silence in seconds.
        sample_rate: Audio sample rate.
    """
    import struct
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    n_samples = int(sample_rate * duration_s)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
