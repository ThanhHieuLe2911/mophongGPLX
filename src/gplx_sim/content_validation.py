from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from gplx_sim.data_builder import database_metadata, validate_content_database


def missing_videos(database_path: Path, videos_directory: Path) -> list[str]:
    with closing(sqlite3.connect(database_path)) as connection:
        filenames = [
            str(row[0])
            for row in connection.execute(
                "SELECT video_filename FROM situations WHERE active = 1 ORDER BY id"
            ).fetchall()
        ]
    return [filename for filename in filenames if not (videos_directory / filename).is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra database và 120 video GPLX")
    parser.add_argument("database", type=Path)
    parser.add_argument("videos", type=Path)
    arguments = parser.parse_args()
    database_path = arguments.database.resolve()
    videos_directory = arguments.videos.resolve()

    validate_content_database(database_path)
    metadata = database_metadata(database_path)
    absent = missing_videos(database_path, videos_directory)
    print(f"Database hợp lệ - phiên bản {metadata.get('content_version', 'không rõ')}")
    if absent:
        print(f"Thiếu {len(absent)}/120 video trong {videos_directory}")
        print("Danh sách thiếu: " + ", ".join(absent))
        return 1
    print(f"Đã đủ 120/120 video trong {videos_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
