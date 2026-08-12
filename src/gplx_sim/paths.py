from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    application_directory: Path
    content_directory: Path
    runtime_directory: Path

    @property
    def content_database(self) -> Path:
        return self.runtime_directory / "content.db"

    @property
    def bundled_content_database(self) -> Path:
        return self.content_directory / "bundled_content.db"

    @property
    def videos_directory(self) -> Path:
        return self.content_directory / "videos"

    @property
    def history_database(self) -> Path:
        return self.runtime_directory / "history.db"

    @classmethod
    def discover(cls) -> "AppPaths":
        if getattr(sys, "frozen", False):
            application_directory = Path(sys.executable).resolve().parent
        else:
            application_directory = Path(__file__).resolve().parents[2]

        content_directory = application_directory / "content"
        runtime_override = os.environ.get("GPLX_RUNTIME_DIR")
        if runtime_override:
            runtime_directory = Path(runtime_override).expanduser().resolve()
        else:
            local_app_data = os.environ.get("LOCALAPPDATA")
            base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
            runtime_directory = base / "MoPhongGPLX"

        return cls(
            application_directory=application_directory,
            content_directory=content_directory,
            runtime_directory=runtime_directory,
        )

    def ensure_directories(self) -> None:
        self.content_directory.mkdir(parents=True, exist_ok=True)
        self.videos_directory.mkdir(parents=True, exist_ok=True)
        self.runtime_directory.mkdir(parents=True, exist_ok=True)
