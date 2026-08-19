import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QMainWindow,
    QMessageBox,
)

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.content_repository import ContentRepository
from gplx_sim.repositories.history_repository import HistoryRepository
from gplx_sim.services.session_service import SessionState
from gplx_sim.ui.main_window import (
    HistoryDialog,
    MainWindow,
    SessionPage,
    SituationSelectionDialog,
    StudySetupPage,
)


def _repository(directory: str) -> ContentRepository:
    root = Path(directory)
    paths = AppPaths(root, root / "content", root / "runtime")
    initialize_databases(paths)
    return ContentRepository(paths.content_database)


def test_study_setup_sources_and_count_selector() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        page = StudySetupPage(_repository(directory))

        # Test that study_setup_page.stack has 3 pages (mode select, practice, exam)
        assert page.stack.count() == 3

        # Test mode cards exist
        assert hasattr(page, 'practice_card')
        assert hasattr(page, 'exam_card')
        assert page.practice_card.mode == "practice"
        assert page.exam_card.mode == "mock_exam"

        # Test practice setup controls exist
        assert hasattr(page, 'practice_start')
        assert hasattr(page, 'practice_summary')
        assert hasattr(page, 'random_source')
        assert hasattr(page, 'practice_custom_source')

        # Test exam setup controls exist
        assert hasattr(page, 'exam_start')
        assert hasattr(page, 'exam_summary')
        assert hasattr(page, 'exam_duration_slider')
        assert page.exam_duration_slider.value() == 10


def test_custom_situation_dialog_lists_filters_and_selects_120_items() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        dialog = SituationSelectionDialog(_repository(directory))

        assert dialog.table.rowCount() == 120
        dialog.chapter.setCurrentIndex(6)
        app.processEvents()
        visible_rows = sum(
            not dialog.table.isRowHidden(row) for row in range(dialog.table.rowCount())
        )
        assert visible_rows == 30

        dialog.search.setText("TH120")
        app.processEvents()
        visible_rows = [
            row
            for row in range(dialog.table.rowCount())
            if not dialog.table.isRowHidden(row)
        ]
        assert visible_rows == [119]
        dialog._row_clicked(119, 3)
        assert dialog.selected_ids == [120]
        assert dialog._selection_boxes[120].isChecked()
        assert dialog._selection_boxes[120].size().width() == 16
        assert dialog._selection_boxes[120].size().height() == 16
        dialog._selection_boxes[120].click()
        assert dialog.selected_ids == []


def test_practice_session_navigation_result_colors_and_hidden_answer_title() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        repository = _repository(directory)
        situations = repository.get_situations_by_ids([1, 2, 3])
        state = SessionState(session_id=1, mode="practice", situations=situations)
        page = SessionPage(Path(directory) / "videos")
        page.begin(state)

        assert page.position_label.text() == "Tự luyện · Tình huống số 1"
        assert situations[0].code not in page.position_label.text()
        assert situations[0].title not in page.position_label.text()
        assert len(page._quick_buttons) == 3

        correct_selections = {
            part.id: next(answer.id for answer in part.answers if answer.is_correct)
            for part in situations[0].parts
        }
        first_part_id, first_answer_id = next(iter(correct_selections.items()))
        page._groups[first_part_id].button(first_answer_id).setChecked(True)
        page._go_to_situation(1)
        page._go_to_situation(0)
        assert page._groups[first_part_id].checkedId() == first_answer_id

        state.submit_current(correct_selections)
        page._update_quick_navigation()
        assert page._quick_buttons[0].property("status") == "correct"

        state.move_to(1)
        wrong_selections = {
            part.id: next(answer.id for answer in part.answers if answer.is_correct)
            for part in situations[1].parts
        }
        first_part = situations[1].parts[0]
        wrong_selections[first_part.id] = next(
            answer.id for answer in first_part.answers if not answer.is_correct
        )
        state.submit_current(wrong_selections)
        page._update_quick_navigation()
        assert page._quick_buttons[1].property("status") == "incorrect"

        page._go_to_situation(2)
        app.processEvents()
        assert state.current_index == 2
        assert page.progress_label.text().startswith("Đang ở câu 3/3")

        page._video_available = True
        page._update_video_duration(30_000)
        page._update_video_position(14_000)
        assert page.video_time_label.text() == "00:14 / 00:30"


def test_session_actions_track_unanswered_parts_and_support_previous_next() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        repository = _repository(directory)
        situations = repository.get_situations_by_ids([1, 2])
        state = SessionState(session_id=1, mode="practice", situations=situations)
        page = SessionPage(Path(directory) / "videos")
        page.begin(state)

        assert page.submit_button.text() == "Còn 4 đáp án chưa chọn"
        assert not page.submit_button.isEnabled()
        assert not page.previous_button.isEnabled()
        assert page.next_button.isEnabled()
        assert page.finish_button.text() == "Kết thúc sớm"

        for selected_count, part in enumerate(situations[0].parts, start=1):
            page._groups[part.id].button(part.answers[0].id).setChecked(True)
            app.processEvents()
            remaining = 4 - selected_count
            expected = (
                "Kiểm tra đáp án"
                if remaining == 0
                else f"Còn {remaining} đáp án chưa chọn"
            )
            assert page.submit_button.text() == expected

        assert page.submit_button.isEnabled()
        page.next_button.click()
        app.processEvents()
        assert state.current_index == 1
        assert page.previous_button.isEnabled()
        assert not page.next_button.isEnabled()
        assert page.submit_button.text() == "Còn 4 đáp án chưa chọn"

        for part in situations[1].parts:
            page._groups[part.id].button(part.answers[0].id).setChecked(True)
        app.processEvents()
        assert page.finish_button.text() == "Kết thúc bài thi"

        page.previous_button.click()
        app.processEvents()
        assert state.current_index == 0
        assert page.submit_button.text() == "Kiểm tra đáp án"
        page.submit_button.click()
        app.processEvents()
        assert page.submit_button.text() == "Đã kiểm tra đáp án"
        assert not page.submit_button.isEnabled()


def test_early_finish_scores_draft_answers_and_zeroes_unanswered_parts(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        root = Path(directory)
        paths = AppPaths(root, root / "content", root / "runtime")
        initialize_databases(paths)
        repository = ContentRepository(paths.content_database)
        history = HistoryRepository(paths.history_database)
        situations = repository.get_situations_by_ids([1, 2])
        session_id = history.start_session("practice", situations)
        state = SessionState(session_id=session_id, mode="practice", situations=situations)

        host = QMainWindow()
        host.history_repository = history
        page = SessionPage(paths.videos_directory)
        host.setCentralWidget(page)
        page.begin(state)

        first_part = situations[0].parts[0]
        correct_answer = next(answer for answer in first_part.answers if answer.is_correct)
        page._groups[first_part.id].button(correct_answer.id).setChecked(True)
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        page.finish_button.click()
        app.processEvents()

        by_situation = {result.situation_id: result for result in state.results}
        assert by_situation[situations[0].id].score == 0.25
        assert by_situation[situations[1].id].score == 0
        saved_session = history.recent_sessions(1)[0]
        assert saved_session["completed_at"] is not None
        assert saved_session["score"] == 0.25


def test_exit_confirmation_discards_session_and_returns_home(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        root = Path(directory)
        paths = AppPaths(root, root / "content", root / "runtime")
        initialize_databases(paths)
        content = ContentRepository(paths.content_database)
        history = HistoryRepository(paths.history_database)
        window = MainWindow(content, history, paths.videos_directory)
        window._start_study_session("practice", "custom", [1], 0)
        assert window.stack.currentWidget() is window.session_page
        assert len(history.recent_sessions()) == 1

        prompts: list[str] = []
        responses = iter(
            [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]
        )

        def confirm(*args, **kwargs):
            prompts.append(args[2])
            return next(responses)

        monkeypatch.setattr(QMessageBox, "question", confirm)
        window.session_page._confirm_exit()
        app.processEvents()
        assert window.stack.currentWidget() is window.session_page
        assert len(history.recent_sessions()) == 1

        window.session_page._confirm_exit()
        app.processEvents()
        assert window.stack.currentWidget() is window.home_page
        assert history.recent_sessions() == []
        assert prompts == [
            "Tiến độ phiên học này sẽ không được lưu, bạn chắc chắn muốn thoát?",
            "Tiến độ phiên học này sẽ không được lưu, bạn chắc chắn muốn thoát?",
        ]


def test_mock_exam_hides_situation_id_and_confirms_completed_exam(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        root = Path(directory)
        paths = AppPaths(root, root / "content", root / "runtime")
        initialize_databases(paths)
        repository = ContentRepository(paths.content_database)
        history = HistoryRepository(paths.history_database)
        situations = repository.get_situations_by_ids([26, 47])
        session_id = history.start_session("mock_exam", situations)
        state = SessionState(session_id=session_id, mode="mock_exam", situations=situations)

        host = QMainWindow()
        host.history_repository = history
        page = SessionPage(paths.videos_directory)
        host.setCentralWidget(page)
        page.begin(state, duration_seconds=15 * 60)

        assert page.position_label.text() == "Thi thử · Câu số 1"
        assert "26" not in page.position_label.text()
        for part in situations[0].parts:
            page._groups[part.id].button(part.answers[0].id).setChecked(True)
        app.processEvents()
        assert page.submit_button.text() == "Nộp câu trả lời"

        page.next_button.click()
        for part in situations[1].parts:
            page._groups[part.id].button(part.answers[0].id).setChecked(True)
        app.processEvents()
        assert page.position_label.text() == "Thi thử · Câu số 2"
        assert page.submit_button.text() == "Hoàn thành bài thi"
        assert page.finish_button.isHidden()

        confirmations: list[str] = []
        responses = iter(
            [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]
        )

        def confirm(*args, **kwargs):
            confirmations.append(args[2])
            return next(responses)

        monkeypatch.setattr(QMessageBox, "question", confirm)
        page.submit_button.click()
        app.processEvents()
        assert not page._is_finished
        assert history.recent_sessions(1)[0]["completed_at"] is None

        page.submit_button.click()
        app.processEvents()
        assert page._is_finished
        assert history.recent_sessions(1)[0]["completed_at"] is not None
        assert confirmations == [
            "Tất cả các câu trả lời đã được ghi, bạn có chắc chắn nộp bài không?",
            "Tất cả các câu trả lời đã được ghi, bạn có chắc chắn nộp bài không?",
        ]


def test_history_dialog_formats_values_and_is_read_only() -> None:
    app = QApplication.instance() or QApplication([])

    class HistoryStub:
        @staticmethod
        def recent_sessions():
            return [
                {
                    "started_at": "2026-08-16T09:08:07",
                    "mode": "practice",
                    "total_situations": 4,
                    "score": 0.750000,
                    "score_on_ten": 1.875,
                    "completed_at": "2026-08-16T09:10:00",
                },
                {
                    "started_at": "2026-08-16T08:00:00",
                    "mode": "mock_exam",
                    "total_situations": 10,
                    "score": None,
                    "score_on_ten": None,
                    "completed_at": None,
                },
            ]

    dialog = HistoryDialog(HistoryStub())
    app.processEvents()

    assert dialog.table.item(0, 0).text() == "16/08/2026, 09:08:07"
    assert dialog.table.item(0, 3).text() == "0.75"
    assert dialog.table.item(0, 4).text() == "1.88"
    assert dialog.table.item(1, 3).text() == "-"
    assert dialog.table.item(1, 5).text() == "Chưa hoàn thành"
    assert dialog.table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert dialog.table.selectionMode() == QAbstractItemView.SelectionMode.NoSelection
    assert dialog.table.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert dialog.table.currentItem() is None
    header = dialog.table.horizontalHeader()
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(5) == QHeaderView.ResizeMode.ResizeToContents
