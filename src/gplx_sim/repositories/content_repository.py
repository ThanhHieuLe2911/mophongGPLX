from __future__ import annotations

import random
import sqlite3
from pathlib import Path

from gplx_sim.domain.models import Answer, QuestionPart, Situation


class ContentRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def count_situations(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM situations WHERE active = 1"
            ).fetchone()
        return int(row["total"])

    def get_random_situations(self, limit: int, answer_limit: int = 3) -> list[Situation]:
        if limit < 1:
            return []
        with self._connect() as connection:
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
        return [self.get_situation(int(row["id"]), answer_limit) for row in rows]

    def get_situation(self, situation_id: int, answer_limit: int = 3) -> Situation:
        with self._connect() as connection:
            situation_row = connection.execute(
                """
                SELECT s.id, s.code, s.title, s.video_filename, c.name AS chapter
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
                answers = self._choose_answers(answer_rows, answer_limit)
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
            video_filename=str(situation_row["video_filename"]),
            parts=tuple(parts),
        )

    @staticmethod
    def _choose_answers(rows: list[sqlite3.Row], answer_limit: int) -> tuple[Answer, ...]:
        answers = [
            Answer(id=int(row["id"]), text=str(row["answer_text"]), is_correct=bool(row["is_correct"]))
            for row in rows
        ]
        correct = [answer for answer in answers if answer.is_correct]
        distractors = [answer for answer in answers if not answer.is_correct]
        if len(correct) != 1:
            raise ValueError("Mỗi phần câu hỏi phải có đúng một đáp án đúng")

        selected = correct + random.sample(distractors, min(max(answer_limit - 1, 0), len(distractors)))
        random.shuffle(selected)
        return tuple(selected)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

