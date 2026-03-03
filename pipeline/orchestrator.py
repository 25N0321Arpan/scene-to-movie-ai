"""Pipeline orchestration — coordinates all five production steps."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel

from pipeline.models import Script
from pipeline.step1_story.script_generator import ScriptGenerator
from pipeline.step2_design.character_designer import CharacterDesigner
from pipeline.step2_design.scene_designer import SceneDesigner
from pipeline.step3_animation.animator import Animator, SceneAssets
from pipeline.step3_animation.motion_prompts import get_motion_prompt
from pipeline.step4_voice.voice_synth import VoiceSynthesizer
from pipeline.step5_editing.audio_mixer import AudioMixer
from pipeline.step5_editing.renderer import FinalRenderer
from pipeline.step5_editing.video_editor import SubtitleEntry, VideoEditor
from utils.file_manager import FileManager
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineConfig(BaseModel):
    """All configuration needed to run the anime pipeline end-to-end."""

    story_provider: str = "gemini"
    story_model: str = "gemini-2.0-flash"
    temperature: float = 0.8
    num_scenes: int = 5
    design_provider: str = "huggingface"
    design_style: str = "anime"
    animation_provider: str = "local"
    voice_provider: str = "edge-tts"
    voice_model: str = "en-US-AriaNeural"
    output_format: str = "mp4"
    fps: int = 24
    resolution: str = "1920x1080"
    output_dir: str = "output"

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            :class:`PipelineConfig` populated from the file.
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(
            story_provider=data.get("story", {}).get("provider", "gemini"),
            story_model=data.get("story", {}).get("model", "gemini-2.0-flash"),
            temperature=data.get("story", {}).get("temperature", 0.8),
            num_scenes=data.get("story", {}).get("num_scenes", 5),
            design_provider=data.get("design", {}).get("provider", "huggingface"),
            design_style=data.get("design", {}).get("style", "anime"),
            animation_provider=data.get("animation", {}).get("provider", "local"),
            voice_provider=data.get("voice", {}).get("provider", "edge-tts"),
            voice_model=data.get("voice", {}).get("default_model", "en-US-AriaNeural"),
            output_format=data.get("editing", {}).get("output_format", "mp4"),
            fps=data.get("editing", {}).get("fps", 24),
            resolution=data.get("editing", {}).get("resolution", "1920x1080"),
            output_dir=data.get("output", {}).get("base_dir", "output"),
        )


class AnimePipeline:
    """Orchestrates the five-step anime creation pipeline.

    Args:
        config: Pipeline configuration object.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.file_manager = FileManager(config.output_dir)
        self._checkpoint: dict = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, story_prompt: str, project_name: str = "anime_project") -> Path:
        """Run the entire pipeline end-to-end.

        Args:
            story_prompt: High-level story premise.
            project_name: Directory name for outputs.

        Returns:
            Path to the final exported video file.
        """
        logger.info(f"Starting pipeline for: {story_prompt[:50]}...")
        project_dir = self.file_manager.create_project_dir(project_name)

        script = self._run_step1(story_prompt, project_dir)
        design_assets = self._run_step2(script, project_dir)
        video_clips = self._run_step3(script, design_assets, project_dir)
        audio_clips = self._run_step4(script, project_dir)
        final_video = self._run_step5(video_clips, audio_clips, script, project_dir)

        logger.info(f"Pipeline complete! Output: {final_video}")
        return final_video

    def run_step(self, step_name: str, **kwargs):
        """Run an individual pipeline step by name.

        Args:
            step_name: One of ``"story"``, ``"design"``, ``"animation"``,
                       ``"voice"``, ``"editing"``.
            **kwargs: Arguments forwarded to the step's runner method.

        Returns:
            The step's output (type varies per step).

        Raises:
            ValueError: If *step_name* is not recognised.
        """
        step_map = {
            "story": self._run_step1,
            "design": self._run_step2,
            "animation": self._run_step3,
            "voice": self._run_step4,
            "editing": self._run_step5,
        }
        if step_name not in step_map:
            raise ValueError(
                f"Unknown step: {step_name!r}. Valid steps: {list(step_map.keys())}"
            )
        return step_map[step_name](**kwargs)

    # ------------------------------------------------------------------
    # Step runners
    # ------------------------------------------------------------------

    def _run_step1(self, story_prompt: str, project_dir: Path) -> Script:
        logger.info("[Step 1/5] Generating script...")
        generator = ScriptGenerator(
            provider=self.config.story_provider,
            model=self.config.story_model,
            temperature=self.config.temperature,
        )
        script = generator.generate_script(
            prompt=story_prompt,
            num_scenes=self.config.num_scenes,
            style=self.config.design_style,
        )
        script_path = project_dir / "scripts" / "script.json"
        script_path.write_text(script.model_dump_json(indent=2))
        logger.info(f"  Script saved: {script_path}")
        return script

    def _run_step2(self, script: Script, project_dir: Path) -> dict:
        logger.info("[Step 2/5] Designing characters and scenes...")
        char_designer = CharacterDesigner(
            provider=self.config.design_provider,
            style=self.config.design_style,
        )
        scene_designer = SceneDesigner(
            provider=self.config.design_provider,
            style=self.config.design_style,
        )
        assets: dict = {"characters": {}, "backgrounds": {}, "scene_images": {}}

        for character in script.characters:
            images = char_designer.generate_character_sheet(character, self.config.design_style)
            assets["characters"][character.name] = images
            logger.info(f"  Character designed: {character.name}")

        for scene in script.scenes:
            bg = scene_designer.generate_background(scene, self.config.design_style)
            assets["backgrounds"][scene.scene_number] = bg
            logger.info(f"  Background designed: Scene {scene.scene_number}")

        return assets

    def _run_step3(self, script: Script, design_assets: dict, project_dir: Path) -> list:
        logger.info("[Step 3/5] Animating scenes...")
        animator = Animator(
            provider=self.config.animation_provider,
            fps=self.config.fps,
        )
        scene_assets: List[SceneAssets] = []
        for scene in script.scenes:
            bg = design_assets["backgrounds"].get(scene.scene_number)
            if bg is None:
                logger.warning(f"  No background for scene {scene.scene_number}, skipping")
                continue
            motion_prompt = get_motion_prompt(scene.mood, "dialogue")
            scene_assets.append(
                SceneAssets(scene=scene, image=bg, motion_prompt=motion_prompt)
            )

        video_clips = animator.batch_animate(scene_assets)
        logger.info(f"  Animated {len(video_clips)} scenes")
        return video_clips

    def _run_step4(self, script: Script, project_dir: Path) -> dict:
        logger.info("[Step 4/5] Synthesizing voices...")
        synth = VoiceSynthesizer(
            provider=self.config.voice_provider,
            model=self.config.voice_model,
        )
        audio_clips: dict = {}

        for scene in script.scenes:
            if self.config.voice_provider == "edge-tts":
                voice_map = {
                    char.name: synth.profile_manager.get_edge_tts_voice(char.name)
                    for char in script.characters
                }
            else:
                voice_map = {
                    char.name: synth.profile_manager.get_voice_id(char.name)
                    for char in script.characters
                }
            clips = synth.synthesize_scene_dialogue(scene, voice_map)
            audio_clips[scene.scene_number] = clips
            logger.info(f"  Voice synthesized: Scene {scene.scene_number}")

        return audio_clips

    def _run_step5(
        self,
        video_clips: list,
        audio_clips: dict,
        script: Script,
        project_dir: Path,
    ) -> Path:
        logger.info("[Step 5/5] Editing and rendering...")
        editor = VideoEditor(fps=self.config.fps, resolution=self.config.resolution)
        mixer = AudioMixer()
        renderer = FinalRenderer(
            output_format=self.config.output_format,
            fps=self.config.fps,
            resolution=self.config.resolution,
        )

        composed_clips = []
        for i, video_clip in enumerate(video_clips):
            scene = script.scenes[i] if i < len(script.scenes) else None
            scene_num = scene.scene_number if scene else i + 1
            clips = audio_clips.get(scene_num, [])
            mixed_audio = mixer.mix_audio(clips) if clips else None

            subtitles: List[SubtitleEntry] = []
            if scene:
                t = 0.0
                for line in scene.dialogue:
                    sub = SubtitleEntry(
                        start_time=t,
                        end_time=t + 3.0,
                        text=line.text,
                        speaker=line.character,
                    )
                    subtitles.append(sub)
                    t += 3.0

            composed = editor.compose_scene_video(
                video_clip,
                [mixed_audio] if mixed_audio else [],
                subtitles,
            )
            composed_clips.append(composed)

        final_video = renderer.render_episode(composed_clips)
        exported = renderer.export(final_video, format=self.config.output_format, quality="high")
        logger.info(f"  Final video: {exported}")

        # Copy final output to project directory
        dest = project_dir / "video" / f"final.{self.config.output_format}"
        import shutil
        shutil.copy2(exported, dest)
        logger.info(f"  Saved to project: {dest}")
        return dest
