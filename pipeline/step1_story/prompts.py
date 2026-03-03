"""Prompt templates for anime script generation."""

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

ANIME_SCRIPT_SYSTEM_PROMPT = """\
You are a professional anime screenwriter with deep knowledge of Japanese animation
storytelling conventions. You craft compelling scripts with:
- Vivid scene descriptions suitable for visual adaptation
- Distinct, memorable characters with clear motivations
- Dramatic dialogue that conveys emotion efficiently
- A clear three-act structure even in short-form stories
- Rich visual and mood cues for every scene

Always respond with ONLY valid JSON matching the requested schema — no markdown
fences, no extra commentary.
"""

# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

ANIME_SCRIPT_USER_PROMPT = """\
Create a {num_scenes}-scene anime script in the "{style}" visual style based on
the following story idea:

"{prompt}"

Return a single JSON object with this exact structure:
{{
  "title": "<episode title>",
  "synopsis": "<one-paragraph synopsis>",
  "characters": [
    {{
      "name": "<character name>",
      "description": "<one sentence about role in story>",
      "personality": "<key personality traits>",
      "appearance": "<physical appearance for illustration>"
    }}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "setting": "<location and time of day>",
      "description": "<2-3 sentence scene description>",
      "mood": "<single word mood, e.g. tense / joyful / melancholic>",
      "visual_notes": "<art direction notes for the animator>",
      "dialogue": [
        {{
          "character": "<character name>",
          "text": "<spoken line>",
          "emotion": "<emotion tag>"
        }}
      ]
    }}
  ]
}}

Produce exactly {num_scenes} scenes.  Make the story engaging and emotionally resonant.
"""

# ---------------------------------------------------------------------------
# Character-profile refinement prompt
# ---------------------------------------------------------------------------

CHARACTER_PROFILE_PROMPT = """\
Expand the following character profile for use in a {style} anime.  Return only JSON
with the keys: name, description, personality, appearance, background, arc.

Character: {character_name}
Context: {context}
"""

# ---------------------------------------------------------------------------
# Scene-description refinement prompt
# ---------------------------------------------------------------------------

SCENE_DESCRIPTION_PROMPT = """\
Rewrite the following scene description to be more visually vivid and suitable for
a {style} anime production.  Focus on:
- Lighting and colour palette
- Character body language and facial expressions
- Camera angle suggestions
- Background detail

Original description:
{description}

Return only the improved description as plain text.
"""
