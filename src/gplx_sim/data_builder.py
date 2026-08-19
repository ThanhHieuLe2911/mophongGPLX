from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from importlib.resources import files
from pathlib import Path


EXPECTED_CHAPTER_COUNTS = {1: 29, 2: 14, 3: 20, 4: 10, 5: 17, 6: 30}


def load_catalog() -> dict:
    resource = files("gplx_sim.data").joinpath("content_catalog.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_catalog(catalog: dict) -> None:
    chapters = catalog.get("chapters", [])
    situations = catalog.get("situations", [])
    if len(chapters) != 6:
        raise ValueError(f"Catalog phải có 6 chương, hiện có {len(chapters)}")
    if len(situations) != 120:
        raise ValueError(f"Catalog phải có 120 tình huống, hiện có {len(situations)}")

    identifiers = [int(situation["id"]) for situation in situations]
    if identifiers != list(range(1, 121)):
        raise ValueError("Tình huống phải được sắp đúng thứ tự từ 1 đến 120")

    chapter_counts = {chapter_id: 0 for chapter_id in EXPECTED_CHAPTER_COUNTS}
    for situation in situations:
        identifier = int(situation["id"])
        expected_code = f"TH{identifier:03d}"
        expected_video = f"{identifier}.mp4"
        if situation["code"] != expected_code:
            raise ValueError(f"Tình huống {identifier} phải có mã {expected_code}")
        if situation["video_filename"] != expected_video:
            raise ValueError(f"Tình huống {identifier} phải dùng video {expected_video}")
        if not str(situation["title"]).strip():
            raise ValueError(f"Tình huống {identifier} chưa có tên")

        chapter_id = int(situation["chapter_id"])
        if chapter_id not in chapter_counts:
            raise ValueError(f"Tình huống {identifier} có chương không hợp lệ")
        chapter_counts[chapter_id] += 1

        parts = situation.get("parts", [])
        if len(parts) != 4:
            raise ValueError(f"Tình huống {identifier} phải có đúng 4 phần")
        for part_number, part in enumerate(parts, start=1):
            answers = part.get("answers", [])
            if len(answers) != 4:
                raise ValueError(
                    f"Tình huống {identifier}, phần {part_number} phải có đúng 4 phương án"
                )
            if sum(bool(answer["is_correct"]) for answer in answers) != 1:
                raise ValueError(
                    f"Tình huống {identifier}, phần {part_number} phải có đúng 1 đáp án đúng"
                )

    if chapter_counts != EXPECTED_CHAPTER_COUNTS:
        raise ValueError(f"Số tình huống theo chương không đúng: {chapter_counts}")


def catalog_checksum(catalog: dict) -> str:
    canonical = json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_content_database(destination: Path, catalog: dict | None = None) -> None:
    catalog = catalog or load_catalog()
    validate_catalog(catalog)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    schema = files("gplx_sim.data").joinpath("schema_content.sql").read_text(encoding="utf-8")

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}_",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary_path)) as connection, connection:
            connection.executescript(schema)
            connection.executemany(
                "INSERT INTO content_metadata(key, value) VALUES (?, ?)",
                (
                    ("schema_version", str(catalog["schema_version"])),
                    ("content_version", str(catalog["content_version"])),
                    ("catalog_sha256", catalog_checksum(catalog)),
                    ("situation_count", "120"),
                ),
            )
            connection.executemany(
                "INSERT INTO chapters(id, code, name) VALUES (?, ?, ?)",
                [
                    (chapter["id"], chapter["code"], chapter["name"])
                    for chapter in catalog["chapters"]
                ],
            )

            part_id = 1
            answer_id = 1
            for situation in catalog["situations"]:
                connection.execute(
                    """
                    INSERT INTO situations(
                        id, code, chapter_id, title, video_filename, active
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        situation["id"],
                        situation["code"],
                        situation["chapter_id"],
                        situation["title"],
                        situation["video_filename"],
                        int(situation.get("active", True)),
                    ),
                )
                for part_order, part in enumerate(situation["parts"], start=1):
                    connection.execute(
                        """
                        INSERT INTO question_parts(
                            id, situation_id, kind, prompt, display_order
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (part_id, situation["id"], part["kind"], part["prompt"], part_order),
                    )
                    for answer_order, answer in enumerate(part["answers"], start=1):
                        connection.execute(
                            """
                            INSERT INTO answers(
                                id, question_part_id, answer_text, is_correct, display_order
                            ) VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                answer_id,
                                part_id,
                                answer["text"],
                                int(answer["is_correct"]),
                                answer_order,
                            ),
                        )
                        answer_id += 1
                    part_id += 1

            connection.execute("ANALYZE")
            connection.execute("PRAGMA optimize")
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def database_metadata(database_path: Path) -> dict[str, str]:
    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute("SELECT key, value FROM content_metadata").fetchall()
    return {str(key): str(value) for key, value in rows}


def validate_content_database(database_path: Path) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        if quick_check != "ok":
            raise ValueError(f"SQLite quick_check thất bại: {quick_check}")
        counts = {
            "chapters": connection.execute("SELECT COUNT(*) FROM chapters").fetchone()[0],
            "situations": connection.execute("SELECT COUNT(*) FROM situations").fetchone()[0],
            "question_parts": connection.execute("SELECT COUNT(*) FROM question_parts").fetchone()[0],
            "answers": connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0],
        }
        expected = {"chapters": 6, "situations": 120, "question_parts": 480, "answers": 1920}
        if counts != expected:
            raise ValueError(f"Số lượng bản ghi không hợp lệ: {counts}")
        invalid_parts = connection.execute(
            """
            SELECT qp.id
            FROM question_parts qp
            LEFT JOIN answers a ON a.question_part_id = qp.id
            GROUP BY qp.id
            HAVING COUNT(a.id) != 4 OR SUM(a.is_correct) != 1
            LIMIT 1
            """
        ).fetchone()
        if invalid_parts is not None:
            raise ValueError(f"Phần câu hỏi {invalid_parts['id']} có đáp án không hợp lệ")
        foreign_key_error = connection.execute("PRAGMA foreign_key_check").fetchone()
        if foreign_key_error is not None:
            raise ValueError("Database có liên kết khóa ngoại không hợp lệ")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo bundled_content.db từ catalog chuẩn")
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    build_content_database(arguments.destination.resolve())
    validate_content_database(arguments.destination.resolve())
    print(f"Đã tạo database nội dung: {arguments.destination.resolve()}")


if __name__ == "__main__":
    main()
