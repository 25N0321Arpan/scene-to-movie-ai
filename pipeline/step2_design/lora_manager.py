"""LoRA model management for character consistency across generated images."""
from typing import Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class LoRAManager:
    """Track and apply LoRA fine-tune weights for individual characters.

    LoRA paths are stored as string identifiers that can be injected into
    Stable Diffusion prompt strings when generating character images.
    """

    def __init__(self):
        self.loaded_models: Dict[str, str] = {}

    def load_lora(self, character_name: str, lora_path: str) -> None:
        """Register a LoRA model for a character.

        Args:
            character_name: Canonical character name used as lookup key.
            lora_path: File path or model identifier for the LoRA weights.
        """
        self.loaded_models[character_name] = lora_path
        logger.info(f"Loaded LoRA for '{character_name}': {lora_path}")

    def get_lora_prompt(self, character_name: str) -> Optional[str]:
        """Return the LoRA prompt trigger string for a character, or None.

        Args:
            character_name: Character to look up.

        Returns:
            A prompt fragment such as ``"<lora:character_name:1>"`` or ``None``
            if no LoRA is registered for that character.
        """
        path = self.loaded_models.get(character_name)
        if path is None:
            return None
        # Derive a clean token name from the path stem
        token = character_name.lower().replace(" ", "_")
        return f"<lora:{token}:1>"

    def unload_lora(self, character_name: str) -> None:
        """Deregister the LoRA model for a character.

        Args:
            character_name: Character whose LoRA should be removed.
        """
        if character_name in self.loaded_models:
            del self.loaded_models[character_name]
            logger.info(f"Unloaded LoRA for '{character_name}'")
        else:
            logger.warning(f"No LoRA registered for '{character_name}'")
