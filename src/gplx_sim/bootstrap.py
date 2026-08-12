from __future__ import annotations

import sqlite3
from importlib.resources import files

from .paths import AppPaths


def initialize_databases(paths: AppPaths) -> None:
    paths.ensure_directories()
    _apply_schema(paths.content_database, "schema_content.sql")
    _apply_schema(paths.history_database, "schema_history.sql")
    _seed_demo_content(paths.content_database)


def _apply_schema(database_path, schema_name: str) -> None:
    schema = files("gplx_sim.data").joinpath(schema_name).read_text(encoding="utf-8")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(schema)


def _seed_demo_content(database_path) -> None:
    with sqlite3.connect(database_path) as connection:
        existing = connection.execute("SELECT COUNT(*) FROM situations").fetchone()[0]
        if existing:
            return

        connection.execute(
            "INSERT INTO chapters(id, code, name) VALUES (1, 'C1', 'Chương 1 - Giao thông đô thị')"
        )
        connection.execute(
            """
            INSERT INTO situations(id, code, chapter_id, title, video_filename)
            VALUES (1, 'TH001', 1, 'Tình huống mẫu: người đi bộ qua đường', '001.mp4')
            """
        )
        parts = [
            (1, "recognition", "Nhận diện tình huống nguy hiểm", 1),
            (2, "indirect", "Dấu hiệu gián tiếp cần chú ý", 2),
            (3, "direct", "Dấu hiệu trực tiếp gây nguy hiểm", 3),
            (4, "handling", "Phương án xử lý phù hợp", 4),
        ]
        connection.executemany(
            """
            INSERT INTO question_parts(id, situation_id, kind, prompt, display_order)
            VALUES (?, 1, ?, ?, ?)
            """,
            parts,
        )

        answer_groups = {
            1: [
                "Người đi bộ có khả năng băng qua đường",
                "Xe phía trước đang đỗ đúng quy định",
                "Đoạn đường hoàn toàn thông thoáng",
                "Không xuất hiện nguy cơ",
            ],
            2: [
                "Khu vực đông dân cư và tầm nhìn bị che khuất",
                "Mặt đường có vạch sơn mới",
                "Trời quang, không mưa",
                "Xe đang đi đúng làn",
            ],
            3: [
                "Người đi bộ bước xuống lòng đường",
                "Cây xanh ở bên đường",
                "Biển quảng cáo phía xa",
                "Xe ngược chiều đang đi bình thường",
            ],
            4: [
                "Giảm tốc độ, quan sát và sẵn sàng dừng lại",
                "Tăng tốc để vượt qua nhanh",
                "Bấm còi liên tục và giữ nguyên tốc độ",
                "Chuyển làn đột ngột",
            ],
        }
        answer_id = 1
        for part_id, answers in answer_groups.items():
            for order, answer_text in enumerate(answers, start=1):
                connection.execute(
                    """
                    INSERT INTO answers(id, question_part_id, answer_text, is_correct, display_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (answer_id, part_id, answer_text, int(order == 1), order),
                )
                answer_id += 1

