import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.content_repository import ContentRepository
from gplx_sim.services.session_service import SessionState
from gplx_sim.ui.main_window import SessionPage, SituationSelectionDialog, StudySetupPage


def _repository(directory: str) -> ContentRepository:
    root = Path(directory)
    paths = AppPaths(root, root / "content", root / "runtime")
    initialize_databases(paths)
    return ContentRepository(paths.content_database)


def test_study_setup_sources_and_count_selector() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gplx_ui_test_") as directory:
        page = StudySetupPage(_repository(directory))

        assert page.question_count.value_box.maximum() == 15
        page.question_count.value_box.setValue(10)
        page.question_count.plus.click()
        app.processEvents()
        assert page.question_count.value() == 11
        page.question_count.value_box.setValue(15)
        assert not page.question_count.plus.isEnabled()

        page.set_source.radio.click()
        app.processEvents()
        assert page.random_row.isHidden()
        assert not page.practice_set_row.isHidden()
        page.custom_source.radio.click()
        app.processEvents()
        assert page.practice_set_row.isHidden()
        assert not page.custom_row.isHidden()

        page.mode.setCurrentIndex(1)
        app.processEvents()
        assert page.source_container.isHidden()
        assert not page.duration_row.isHidden()


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
