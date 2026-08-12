from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SessionMode(str, Enum):
    PRACTICE = "practice"
    EXAM = "exam"


@dataclass(frozen=True, slots=True)
class Answer:
    id: int
    text: str
    is_correct: bool


@dataclass(frozen=True, slots=True)
class QuestionPart:
    id: int
    kind: str
    prompt: str
    answers: tuple[Answer, ...]


@dataclass(frozen=True, slots=True)
class Situation:
    id: int
    code: str
    title: str
    chapter: str
    video_filename: str
    parts: tuple[QuestionPart, ...]

    def video_path(self, videos_directory: Path) -> Path:
        return videos_directory / self.video_filename


@dataclass(frozen=True, slots=True)
class PartResult:
    part_id: int
    selected_answer_id: int | None
    correct_answer_id: int
    is_correct: bool


@dataclass(frozen=True, slots=True)
class SituationResult:
    situation_id: int
    parts: tuple[PartResult, ...]

    @property
    def correct_parts(self) -> int:
        return sum(result.is_correct for result in self.parts)

    @property
    def score(self) -> float:
        return self.correct_parts * 0.25

