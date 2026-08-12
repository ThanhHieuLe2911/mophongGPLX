from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from importlib.resources import files
from pathlib import Path

from .data_builder import (
    build_content_database,
    catalog_checksum,
    database_metadata,
    load_catalog,
    validate_content_database,
)
from .paths import AppPaths


class ContentInitializationError(RuntimeError):
    pass


def initialize_databases(paths: AppPaths) -> None:
    paths.ensure_directories()
    _ensure_bundled_content(paths.bundled_content_database)
    _install_or_refresh_active_content(
        paths.bundled_content_database,
        paths.content_database,
    )
    _apply_history_schema(paths.history_database)


def _ensure_bundled_content(database_path: Path) -> None:
    catalog = load_catalog()
    expected_version = str(catalog["content_version"])
    expected_checksum = catalog_checksum(catalog)
    try:
        metadata = database_metadata(database_path)
        validate_content_database(database_path)
    except (OSError, sqlite3.DatabaseError, ValueError):
        metadata = {}
    if (
        metadata.get("content_version") != expected_version
        or metadata.get("catalog_sha256") != expected_checksum
    ):
        build_content_database(database_path, catalog)
        validate_content_database(database_path)


def _install_or_refresh_active_content(bundled_path: Path, active_path: Path) -> None:
    bundled_metadata = database_metadata(bundled_path)
    replace_active = not active_path.is_file()
    if not replace_active:
        try:
            active_metadata = database_metadata(active_path)
            validate_content_database(active_path)
            replace_active = (
                active_metadata.get("content_version") != bundled_metadata.get("content_version")
                or active_metadata.get("catalog_sha256") != bundled_metadata.get("catalog_sha256")
            )
        except (OSError, sqlite3.DatabaseError, ValueError):
            replace_active = True

    if not replace_active:
        return
    if active_path.is_file():
        backup_path = active_path.with_name("content.before_update.db")
        shutil.copy2(active_path, backup_path)
    temporary_path = active_path.with_name("content.installing.db")
    try:
        shutil.copy2(bundled_path, temporary_path)
        temporary_path.replace(active_path)
    except OSError as error:
        raise ContentInitializationError(f"Không thể cài database nội dung: {error}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def _apply_history_schema(database_path: Path) -> None:
    schema = files("gplx_sim.data").joinpath("schema_history.sql").read_text(encoding="utf-8")
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.executescript(schema)
