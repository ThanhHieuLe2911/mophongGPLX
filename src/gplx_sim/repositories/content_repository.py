from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

from gplx_sim.domain.models import (
    EXAM_CHAPTER_DISTRIBUTION,
    Answer,
    ChapterSummary,
    QuestionPart,
    Situation,
    SituationSummary,
)


class ContentRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def count_situations(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM situations WHERE active = 1"
            ).fetchone()
        return int(row["total"])

    def get_all_situations(self) -> list[Situation]:
        """Lấy tất cả các tình huống đang hoạt động, sắp xếp theo ID."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id FROM situations WHERE active = 1 ORDER BY id"
            ).fetchall()
        return [self.get_situation(int(row["id"])) for row in rows]

    def get_random_situations(self, limit: int) -> list[Situation]:
        """Bốc ngẫu nhiên không theo chương (giữ để tương thích).

        Logic bốc đề có cấu trúc nằm ở ``get_exam_situations``.
        """
        if limit < 1:
            return []
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT s.id
                FROM situations s
                WHERE s.active = 1
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self.get_situation(int(row["id"])) for row in rows]

    def get_exam_situations(
        self,
        distribution: Mapping[int, int] | None = None,
    ) -> list[Situation]:
        """Bốc đề theo cấu trúc chương đã quy định.

        Mặc định dùng ``EXAM_CHAPTER_DISTRIBUTION`` (2-1-2-1-2-2 = 10 câu).
        Trong mỗi chương chọn ngẫu nhiên; thứ tự chương được giữ nguyên.
        """
        plan = dict(distribution or EXAM_CHAPTER_DISTRIBUTION)
        if not plan:
            return []
        ordered_chapters = sorted(plan.items())
        chapter_ids = [chapter_id for chapter_id, _ in ordered_chapters]
        counts = [count for _, count in ordered_chapters]

        with closing(self._connect()) as connection:
            placeholders = ", ".join("?" for _ in chapter_ids)
            rows = connection.execute(
                f"""
                SELECT id, chapter_id
                FROM situations
                WHERE active = 1 AND chapter_id IN ({placeholders})
                ORDER BY chapter_id, RANDOM()
                """,
                chapter_ids,
            ).fetchall()

        grouped: dict[int, list[int]] = {chapter_id: [] for chapter_id in chapter_ids}
        for row in rows:
            grouped[int(row["chapter_id"])].append(int(row["id"]))

        selected_ids: list[int] = []
        for chapter_id, needed in ordered_chapters:
            available = grouped.get(chapter_id, [])
            if len(available) < needed:
                raise LookupError(
                    f"Chương {chapter_id} chỉ có {len(available)} tình huống, "
                    f"cần {needed} để bốc đề."
                )
            selected_ids.extend(available[:needed])

        return self.get_situations_by_ids(selected_ids)

    def list_chapters(self) -> list[ChapterSummary]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, code, name FROM chapters ORDER BY id"
            ).fetchall()
        return [
            ChapterSummary(id=int(row["id"]), code=str(row["code"]), name=str(row["name"]))
            for row in rows
        ]

    def list_situations(self) -> list[SituationSummary]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id, s.code, s.chapter_id, c.name AS chapter_name,
                    s.title, s.video_filename
                FROM situations s
                JOIN chapters c ON c.id = s.chapter_id
                WHERE s.active = 1
                ORDER BY s.id
                """
            ).fetchall()
        return [
            SituationSummary(
                id=int(row["id"]),
                code=str(row["code"]),
                chapter_id=int(row["chapter_id"]),
                chapter_name=str(row["chapter_name"]),
                title=str(row["title"]),
                video_filename=str(row["video_filename"]),
            )
            for row in rows
        ]

    def get_situations_by_ids(self, situation_ids: list[int]) -> list[Situation]:
        ordered_ids = list(dict.fromkeys(int(identifier) for identifier in situation_ids))
        if not ordered_ids:
            return []
        placeholders = ", ".join("?" for _ in ordered_ids)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT id FROM situations WHERE active = 1 AND id IN ({placeholders})",
                ordered_ids,
            ).fetchall()
        available_ids = {int(row["id"]) for row in rows}
        missing_ids = [identifier for identifier in ordered_ids if identifier not in available_ids]
        if missing_ids:
            raise LookupError(
                "Không tìm thấy tình huống đang hoạt động: "
                + ", ".join(str(identifier) for identifier in missing_ids)
            )
        return [self.get_situation(identifier) for identifier in ordered_ids]

    def get_situation(self, situation_id: int) -> Situation:
        with closing(self._connect()) as connection:
            situation_row = connection.execute(
                """
                SELECT s.id, s.code, s.title, s.chapter_id, s.video_filename, c.name AS chapter
                FROM situations s
                JOIN chapters c ON c.id = s.chapter_id
                WHERE s.id = ?
                """,
                (situation_id,),
            ).fetchone()
            if situation_row is None:
                raise LookupError(f"Không tìm thấy tình huống {situation_id}")

            part_rows = connection.execute(
                """
                SELECT id, kind, prompt
                FROM question_parts
                WHERE situation_id = ?
                ORDER BY display_order
                """,
                (situation_id,),
            ).fetchall()

            parts: list[QuestionPart] = []
            for part_row in part_rows:
                answer_rows = connection.execute(
                    """
                    SELECT id, answer_text, is_correct
                    FROM answers
                    WHERE question_part_id = ?
                    ORDER BY display_order
                    """,
                    (part_row["id"],),
                ).fetchall()
                answers = self._load_answers(answer_rows)
                parts.append(
                    QuestionPart(
                        id=int(part_row["id"]),
                        kind=str(part_row["kind"]),
                        prompt=str(part_row["prompt"]),
                        answers=answers,
                    )
                )

        return Situation(
            id=int(situation_row["id"]),
            code=str(situation_row["code"]),
            title=str(situation_row["title"]),
            chapter=str(situation_row["chapter"]),
            chapter_id=int(situation_row["chapter_id"]),
            video_filename=str(situation_row["video_filename"]),
            parts=tuple(parts),
        )

    @staticmethod
    def _load_answers(rows: list[sqlite3.Row]) -> tuple[Answer, ...]:
        answers = [
            Answer(id=int(row["id"]), text=str(row["answer_text"]), is_correct=bool(row["is_correct"]))
            for row in rows
        ]
        correct = [answer for answer in answers if answer.is_correct]
        if len(answers) != 4:
            raise ValueError("Mỗi phần câu hỏi phải có đúng bốn phương án")
        if len(correct) != 1:
            raise ValueError("Mỗi phần câu hỏi phải có đúng một đáp án đúng")
        return tuple(answers)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
