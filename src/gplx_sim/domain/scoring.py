from __future__ import annotations

from collections.abc import Mapping

from .models import PartResult, Situation, SituationResult


def grade_situation(
    situation: Situation,
    selected_answers: Mapping[int, int],
) -> SituationResult:
    """Chấm bốn phần của một tình huống, mỗi phần đúng được 0,25 điểm."""
    results: list[PartResult] = []
    for part in situation.parts:
        correct = next((answer for answer in part.answers if answer.is_correct), None)
        if correct is None:
            raise ValueError(f"Phần câu hỏi {part.id} không có đáp án đúng")

        selected_id = selected_answers.get(part.id)
        results.append(
            PartResult(
                part_id=part.id,
                selected_answer_id=selected_id,
                correct_answer_id=correct.id,
                is_correct=selected_id == correct.id,
            )
        )

    return SituationResult(situation_id=situation.id, parts=tuple(results))


def score_on_ten(
    results: list[SituationResult],
    total_situations: int | None = None,
) -> float:
    denominator = total_situations if total_situations is not None else len(results)
    if denominator <= 0:
        return 0.0
    raw_score = sum(result.score for result in results)
    return round(raw_score / denominator * 10, 2)
