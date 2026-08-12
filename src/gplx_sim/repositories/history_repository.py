from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from gplx_sim.domain.models import Situation, SituationResult


class HistoryRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def start_session(self, mode: str, situations: list[Situation]) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions(mode, started_at, total_situations)
                VALUES (?, ?, ?)
                """,
                (mode, datetime.now().isoformat(timespec="seconds"), len(situations)),
            )
            session_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO session_situations(
                    session_id, situation_id, situation_code, situation_title, display_order
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (session_id, situation.id, situation.code, situation.title, index)
                    for index, situation in enumerate(situations, start=1)
                ],
            )
        return session_id

    def complete_session(
        self,
        session_id: int,
        situations: list[Situation],
        results: list[SituationResult],
        score_on_ten: float,
    ) -> None:
        by_situation = {result.situation_id: result for result in results}
        with self._connect() as connection:
            for situation in situations:
                result = by_situation.get(situation.id)
                if result is None:
                    continue
                row = connection.execute(
                    """
                    SELECT id FROM session_situations
                    WHERE session_id = ? AND situation_id = ?
                    """,
                    (session_id, situation.id),
                ).fetchone()
                session_situation_id = int(row["id"])
                connection.execute(
                    "UPDATE session_situations SET score = ? WHERE id = ?",
                    (result.score, session_situation_id),
                )
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO session_answers(
                        session_situation_id, part_id, selected_answer_id,
                        correct_answer_id, is_correct
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            session_situation_id,
                            part.part_id,
                            part.selected_answer_id,
                            part.correct_answer_id,
                            int(part.is_correct),
                        )
                        for part in result.parts
                    ],
                )

            connection.execute(
                """
                UPDATE sessions
                SET completed_at = ?, score = ?, score_on_ten = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    sum(result.score for result in results),
                    score_on_ten,
                    session_id,
                ),
            )

    def recent_sessions(self, limit: int = 50) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT id, mode, started_at, completed_at, total_situations, score, score_on_ten
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

