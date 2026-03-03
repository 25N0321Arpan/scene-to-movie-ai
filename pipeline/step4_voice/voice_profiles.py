"""Character voice profile management."""
from typing import Dict, Optional

from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


class VoiceProfile(BaseModel):
    """ElevenLabs voice settings for a character.

    Attributes:
        character_name: Canonical character name.
        voice_id: ElevenLabs voice identifier.
        stability: Voice stability (0–1).
        similarity_boost: Similarity boost (0–1).
        style: Style exaggeration (0–1).
        use_speaker_boost: Whether to enable speaker boost.
    """

    character_name: str
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


# Default ElevenLabs voice IDs (public voices)
DEFAULT_VOICES: Dict[str, str] = {
    "narrator": "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "hero": "AZnzlk1XvdvUeBnXmlld",        # Domi
    "villain": "EXAVITQu4vr4xnSDxMaL",     # Bella
    "support": "ErXwobaYiN019PkySvjV",      # Antoni
    "default": "21m00Tcm4TlvDq8ikWAM",     # Rachel fallback
}

# Default Edge TTS voice names — free, no API key required
# See: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
EDGE_TTS_VOICES: Dict[str, str] = {
    "narrator": "en-US-AriaNeural",       # English female (narrator)
    "hero": "en-US-GuyNeural",            # English male
    "heroine": "en-US-JennyNeural",       # English female
    "villain": "en-US-DavisNeural",       # English male (deeper)
    "support": "en-US-JaneNeural",        # English female (support)
    # Japanese anime voices
    "hero_ja": "ja-JP-KeitaNeural",       # Japanese male
    "heroine_ja": "ja-JP-NanamiNeural",   # Japanese female
    "default": "en-US-AriaNeural",        # Default fallback
}


class VoiceProfileManager:
    """Manage voice profiles for all characters in a project."""

    def __init__(self):
        self.profiles: Dict[str, VoiceProfile] = {}
        self._load_default_profiles()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def _load_default_profiles(self) -> None:
        """Populate profiles dict from :data:`DEFAULT_VOICES`."""
        for role, voice_id in DEFAULT_VOICES.items():
            profile = VoiceProfile(character_name=role, voice_id=voice_id)
            self.profiles[role.lower()] = profile
        logger.debug(f"Loaded {len(self.profiles)} default voice profiles")

    def get_profile(self, character_name: str) -> Optional[VoiceProfile]:
        """Return the voice profile for *character_name*, or ``None``.

        Args:
            character_name: Character name to look up.

        Returns:
            :class:`VoiceProfile` or ``None`` if not found.
        """
        return self.profiles.get(character_name.lower())

    def set_profile(self, profile: VoiceProfile) -> None:
        """Register or update a voice profile.

        Args:
            profile: :class:`VoiceProfile` to store.
        """
        self.profiles[profile.character_name.lower()] = profile
        logger.info(f"Set voice profile for '{profile.character_name}': {profile.voice_id}")

    def get_voice_id(self, character_name: str) -> str:
        """Return the ElevenLabs voice ID for a character.

        Falls back to the ``"default"`` voice if no specific profile exists.

        Args:
            character_name: Character name to look up.

        Returns:
            ElevenLabs voice ID string.
        """
        profile = self.get_profile(character_name)
        if profile:
            return profile.voice_id
        logger.debug(
            f"No voice profile for '{character_name}', using default voice"
        )
        return DEFAULT_VOICES["default"]

    def get_edge_tts_voice(self, character_name: str) -> str:
        """Return the Edge TTS voice name for a character.

        Matches character names to roles heuristically, falling back to the
        ``"default"`` Edge TTS voice.

        Args:
            character_name: Character name to look up.

        Returns:
            Edge TTS voice name string.
        """
        name_lower = character_name.lower()
        if name_lower in EDGE_TTS_VOICES:
            return EDGE_TTS_VOICES[name_lower]
        # Heuristic role matching
        for role in ("narrator", "hero", "heroine", "villain", "support"):
            if role in name_lower:
                return EDGE_TTS_VOICES[role]
        return EDGE_TTS_VOICES["default"]
