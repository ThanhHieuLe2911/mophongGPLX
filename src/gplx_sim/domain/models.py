from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SessionMode(str, Enum):
    PRACTICE = "practice"
    MOCK_EXAM = "mock_exam"
    OFFICIAL_EXAM = "official_exam"


# Cấu trúc đề thi cố định: mỗi chương lấy đúng số câu quy định.
# Tổng cộng 10 câu, đúng thứ tự chương 1 -> 6.
EXAM_CHAPTER_DISTRIBUTION: dict[int, int] = {
    1: 2,
    2: 1,
    3: 2,
    4: 1,
    5: 2,
    6: 2,
}
EXAM_TOTAL_SITUATIONS = sum(EXAM_CHAPTER_DISTRIBUTION.values())


@dataclass(frozen=True, slots=True)
class ChapterSummary:
    id: int
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class SituationSummary:
    id: int
    code: str
    chapter_id: int
    chapter_name: str
    title: str
    video_filename: str


@dataclass(frozen=True, slots=True)
class PracticeSetSummary:
    id: int
    code: str
    name: str
    situation_count: int


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
