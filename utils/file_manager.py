"""File and directory management utilities."""
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manages project output directories and file paths."""

    def __init__(self, base_dir: str = "output"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_project_dir(self, project_name: str) -> Path:
        """Create a new project output directory with standard subdirectories.

        Args:
            project_name: Name of the project (used as directory name).

        Returns:
            Path to the created project directory.
        """
        project_dir = self.base_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ["images", "audio", "video", "scripts"]:
            (project_dir / subdir).mkdir(exist_ok=True)
        logger.info(f"Created project directory: {project_dir}")
        return project_dir

    def cleanup_temp_files(self, directory: Path) -> None:
        """Remove temporary ``*.tmp`` files from *directory*.

        Args:
            directory: Directory to scan for temp files.
        """
        removed = 0
        for tmp_file in directory.rglob("*.tmp"):
            try:
                tmp_file.unlink()
                removed += 1
            except OSError as exc:
                logger.warning(f"Could not remove {tmp_file}: {exc}")
        logger.info(f"Cleaned up {removed} temp files in {directory}")

    def get_output_path(self, project_dir: Path, step: str, filename: str) -> Path:
        """Get (and create if needed) the output path for a file in a pipeline step.

        Args:
            project_dir: Root directory of the project.
            step: Sub-directory name corresponding to the pipeline step.
            filename: Target filename.

        Returns:
            Full :class:`~pathlib.Path` to the output file.
        """
        step_dir = project_dir / step
        step_dir.mkdir(exist_ok=True)
        return step_dir / filename
