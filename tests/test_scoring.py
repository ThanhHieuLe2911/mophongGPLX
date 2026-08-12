import unittest

from gplx_sim.domain.models import Answer, QuestionPart, Situation
from gplx_sim.domain.scoring import grade_situation, score_on_ten


def make_situation() -> Situation:
    parts = tuple(
        QuestionPart(
            id=part_id,
            kind=f"part-{part_id}",
            prompt="Câu hỏi",
            answers=(
                Answer(id=part_id * 10 + 1, text="Đúng", is_correct=True),
                Answer(id=part_id * 10 + 2, text="Sai", is_correct=False),
            ),
        )
        for part_id in range(1, 5)
    )
    return Situation(1, "TH001", "Mẫu", "Chương 1", "001.mp4", parts)


class ScoringTests(unittest.TestCase):
    def test_four_correct_parts_equal_one_point(self) -> None:
        situation = make_situation()
        selections = {part.id: part.answers[0].id for part in situation.parts}
        result = grade_situation(situation, selections)
        self.assertEqual(result.correct_parts, 4)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(score_on_ten([result]), 10.0)

    def test_missing_answer_scores_zero_for_that_part(self) -> None:
        result = grade_situation(make_situation(), {})
        self.assertEqual(result.correct_parts, 0)
        self.assertEqual(result.score, 0.0)


if __name__ == "__main__":
    unittest.main()
