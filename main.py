"""Main entry point for the Anime Creation Pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from pipeline.orchestrator import AnimePipeline, PipelineConfig
from utils.logger import get_logger, setup_logging

load_dotenv()
console = Console()
logger = get_logger(__name__)


@click.command()
@click.option("--prompt", "-p", default=None, help="Story prompt / idea for the anime")
@click.option("--config", "-c", default="config.yaml", help="Path to config YAML file")
@click.option(
    "--steps",
    "-s",
    default=None,
    help="Comma-separated steps to run (e.g. 1,2,3)",
)
@click.option(
    "--resume",
    "-r",
    default=None,
    help="Resume from an existing project directory",
)
@click.option("--output-dir", "-o", default=None, help="Override output directory")
@click.option("--num-scenes", "-n", default=None, type=int, help="Number of scenes to generate")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG/INFO/WARNING/ERROR)",
)
def main(
    prompt: str | None,
    config: str,
    steps: str | None,
    resume: str | None,
    output_dir: str | None,
    num_scenes: int | None,
    log_level: str,
) -> None:
    """AI-powered Anime Creation Pipeline.

    Transform your story idea into a fully rendered anime video with
    voice acting, animation, and editing — all orchestrated through Python.
    """
    setup_logging(log_level)

    console.print(
        Panel.fit(
            "[bold cyan]🎬 Anime Creation Pipeline[/bold cyan]\n"
            "[dim]Powered by AI — Script → Design → Animation → Voice → Edit[/dim]",
            border_style="cyan",
        )
    )

    # ------------------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------------------
    if Path(config).exists():
        pipeline_config = PipelineConfig.from_yaml(config)
    else:
        pipeline_config = PipelineConfig()
        logger.warning(f"Config file {config!r} not found, using defaults.")

    if output_dir:
        pipeline_config.output_dir = output_dir
    if num_scenes:
        pipeline_config.num_scenes = num_scenes

    # ------------------------------------------------------------------
    # Handle --resume
    # ------------------------------------------------------------------
    if resume:
        resume_path = Path(resume)
        if not resume_path.exists():
            console.print(f"[red]Resume directory not found: {resume}[/red]")
            sys.exit(1)
        script_path = resume_path / "scripts" / "script.json"
        if not script_path.exists():
            console.print(f"[red]No script found in {resume}. Cannot resume.[/red]")
            sys.exit(1)
        console.print(f"[yellow]Resuming from: {resume}[/yellow]")
        prompt = prompt or "resumed project"

    # ------------------------------------------------------------------
    # Require a prompt
    # ------------------------------------------------------------------
    if not prompt:
        console.print("[red]Please provide a story prompt with --prompt[/red]")
        console.print(
            "[dim]Example: python main.py --prompt "
            "'A samurai discovers a hidden world...'[/dim]"
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Run pipeline
    # ------------------------------------------------------------------
    pipeline = AnimePipeline(config=pipeline_config)

    if steps:
        step_list = [s.strip() for s in steps.split(",")]
        step_name_map = {
            "1": "story",
            "2": "design",
            "3": "animation",
            "4": "voice",
            "5": "editing",
        }
        for step in step_list:
            step_name = step_name_map.get(step, step)
            console.print(f"[cyan]Running step: {step_name}[/cyan]")
            logger.info(f"Running step: {step_name}")
    else:
        project_name = prompt[:30].replace(" ", "_").replace("/", "_").lower()
        console.print(f"\n[green]Story:[/green] {prompt}")
        console.print(f"[green]Scenes:[/green] {pipeline_config.num_scenes}")
        console.print(f"[green]Provider:[/green] {pipeline_config.story_provider}\n")
        try:
            output = pipeline.run(story_prompt=prompt, project_name=project_name)
            console.print("\n[bold green]✅ Pipeline complete![/bold green]")
            console.print(f"[green]Output:[/green] {output}")
        except Exception as e:
            console.print(f"\n[bold red]❌ Pipeline failed:[/bold red] {e}")
            logger.exception("Pipeline failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
