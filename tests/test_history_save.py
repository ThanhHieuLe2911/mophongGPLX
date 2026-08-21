import tempfile
import unittest
from pathlib import Path

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.domain.models import Situation, PartResult, SituationResult
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.history_repository import HistoryRepository
from gplx_sim.services.session_service import SessionState


class HistorySaveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="gplx_test_history_")
        self.root = Path(self.directory.name)
        self.paths = AppPaths(self.root, self.root / "content", self.root / "runtime")
        initialize_databases(self.paths)
        self.history_repo = HistoryRepository(self.paths.history_database)

    def tearDown(self):
        self.directory.cleanup()

    def _create_mock_situations(self) -> list[Situation]:
        return [
            Situation(
                id=1,
                code="TH001",
                title="Test 1",
                chapter="Chapter 1",
                chapter_id=1,
                video_filename="1.mp4",
                parts=(),
            ),
            Situation(
                id=2,
                code="TH002",
                title="Test 2",
                chapter="Chapter 1",
                chapter_id=1,
                video_filename="2.mp4",
                parts=(),
            ),
        ]

    def test_practice_mode_does_not_save_to_history_when_discarded(self):
        situations = self._create_mock_situations()
        session_id = self.history_repo.start_session("practice", situations)
        self.history_repo.discard_session(session_id)

        recent = self.history_repo.recent_sessions()
        session_ids = [row["id"] for row in recent]
        self.assertNotIn(session_id, session_ids)

    def test_mock_exam_mode_saves_to_history_when_completed(self):
        situations = self._create_mock_situations()
        session_id = self.history_repo.start_session("mock_exam", situations)
        result = SituationResult(situation_id=1, parts=(PartResult(part_id=1, selected_answer_id=1, correct_answer_id=1, is_correct=True),))
        self.history_repo.complete_session(session_id, situations, [result], 10.0)

        recent = self.history_repo.recent_sessions()
        session_ids = [row["id"] for row in recent]
        self.assertIn(session_id, session_ids)

    def test_chapter_test_mode_saves_to_history_when_completed(self):
        situations = self._create_mock_situations()
        session_id = self.history_repo.start_session("chapter_test", situations)
        result = SituationResult(situation_id=1, parts=(PartResult(part_id=1, selected_answer_id=1, correct_answer_id=1, is_correct=True),))
        self.history_repo.complete_session(session_id, situations, [result], 10.0)

        recent = self.history_repo.recent_sessions()
        session_ids = [row["id"] for row in recent]
        self.assertIn(session_id, session_ids)

    def test_session_state_finish_with_save_history_true(self):
        situations = self._create_mock_situations()
        session_id = self.history_repo.start_session("mock_exam", situations)
        state = SessionState(session_id=session_id, mode="mock_exam", situations=situations)
        state.finish(self.history_repo, save_history=True)

        recent = self.history_repo.recent_sessions()
        session_ids = [row["id"] for row in recent]
        self.assertIn(session_id, session_ids)

    def test_session_state_finish_with_save_history_false(self):
        situations = self._create_mock_situations()
        session_id = self.history_repo.start_session("practice", situations)
        state = SessionState(session_id=session_id, mode="practice", situations=situations)
        state.finish(self.history_repo, save_history=False)

        recent = self.history_repo.recent_sessions()
        session_ids = [row["id"] for row in recent]
        self.assertNotIn(session_id, session_ids)


if __name__ == "__main__":
    unittest.main()
