import unittest

from gplx_sim.domain.models import Answer, QuestionPart, Situation
from gplx_sim.domain.scoring import grade_situation, score_on_ten
from gplx_sim.services.session_service import SessionState


def make_situation(situation_id: int = 1) -> Situation:
    parts = tuple(
        QuestionPart(
            id=situation_id * 100 + part_id,
            kind=f"part-{part_id}",
            prompt="Câu hỏi",
            answers=(
                Answer(id=situation_id * 1000 + part_id * 10 + 1, text="Đúng", is_correct=True),
                Answer(id=situation_id * 1000 + part_id * 10 + 2, text="Sai", is_correct=False),
            ),
        )
        for part_id in range(1, 5)
    )
    return Situation(
        situation_id,
        f"TH{situation_id:03d}",
        "Mẫu",
        "Chương 1",
        f"{situation_id:03d}.mp4",
        parts,
    )


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

    def test_score_uses_total_situation_count_after_timeout(self) -> None:
        situation = make_situation()
        selections = {part.id: part.answers[0].id for part in situation.parts}
        result = grade_situation(situation, selections)
        self.assertEqual(score_on_ten([result], total_situations=10), 1.0)

    def test_timeout_marks_every_unanswered_situation_as_zero(self) -> None:
        state = SessionState(
            session_id=1,
            mode="mock_exam",
            situations=[make_situation(1), make_situation(2)],
        )

        state.complete_unanswered()

        self.assertEqual(len(state.results), 2)
        self.assertTrue(all(result.score == 0 for result in state.results))


if __name__ == "__main__":
    unittest.main()
