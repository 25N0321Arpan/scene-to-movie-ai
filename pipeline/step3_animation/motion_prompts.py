"""Motion prompt templates for scene animation."""
from typing import Dict

# ---------------------------------------------------------------------------
# Constant prompt templates
# ---------------------------------------------------------------------------

ACTION_MOTION_PROMPT = (
    "dynamic camera movement, fast panning, intense motion blur, "
    "action-packed movement, high energy animation"
)

DIALOGUE_MOTION_PROMPT = (
    "subtle camera drift, gentle zoom in on speaker, soft bokeh, "
    "natural ambient motion, calm steady movement"
)

EMOTIONAL_MOTION_PROMPT = (
    "slow zoom in, gentle parallax, soft focus pull, "
    "emotional swell, contemplative camera drift"
)

TRANSITION_MOTION_PROMPT = (
    "smooth camera pan across the scene, gentle fade motion, "
    "cinematic wide sweep, establishing shot movement"
)

# ---------------------------------------------------------------------------
# Mood → prompt mapping
# ---------------------------------------------------------------------------

_MOOD_MAP: Dict[str, str] = {
    "tense": ACTION_MOTION_PROMPT,
    "action": ACTION_MOTION_PROMPT,
    "intense": ACTION_MOTION_PROMPT,
    "joyful": DIALOGUE_MOTION_PROMPT,
    "happy": DIALOGUE_MOTION_PROMPT,
    "calm": DIALOGUE_MOTION_PROMPT,
    "neutral": DIALOGUE_MOTION_PROMPT,
    "melancholic": EMOTIONAL_MOTION_PROMPT,
    "sad": EMOTIONAL_MOTION_PROMPT,
    "nostalgic": EMOTIONAL_MOTION_PROMPT,
    "mysterious": EMOTIONAL_MOTION_PROMPT,
    "hopeful": EMOTIONAL_MOTION_PROMPT,
    "transition": TRANSITION_MOTION_PROMPT,
    "establishing": TRANSITION_MOTION_PROMPT,
}

_SCENE_TYPE_MAP: Dict[str, str] = {
    "dialogue": DIALOGUE_MOTION_PROMPT,
    "action": ACTION_MOTION_PROMPT,
    "emotional": EMOTIONAL_MOTION_PROMPT,
    "transition": TRANSITION_MOTION_PROMPT,
}


def get_motion_prompt(mood: str, scene_type: str) -> str:
    """Return the most appropriate motion prompt for a scene.

    Checks *mood* first, then falls back to *scene_type*, then defaults to the
    dialogue motion prompt.

    Args:
        mood: Scene mood string (e.g. ``"tense"``, ``"melancholic"``).
        scene_type: Broad category (e.g. ``"action"``, ``"dialogue"``).

    Returns:
        Motion prompt string ready to pass to an animation API.
    """
    key = mood.lower().strip() if mood else ""
    if key in _MOOD_MAP:
        return _MOOD_MAP[key]

    key2 = scene_type.lower().strip() if scene_type else ""
    if key2 in _SCENE_TYPE_MAP:
        return _SCENE_TYPE_MAP[key2]

    return DIALOGUE_MOTION_PROMPT
