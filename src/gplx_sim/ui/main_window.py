from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gplx_sim.domain.models import Situation, SituationResult
from gplx_sim.repositories.content_repository import ContentRepository
from gplx_sim.repositories.history_repository import HistoryRepository
from gplx_sim.services.session_service import SessionState


class SetupPage(QWidget):
    start_requested = Signal(str, int, int)
    history_requested = Signal()

    def __init__(self, situation_count: int):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 44, 64, 44)
        layout.setSpacing(24)

        heading = QLabel("MÔ PHỎNG TÌNH HUỐNG GIAO THÔNG")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Tự luyện và thi thử hoàn toàn offline")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(32, 28, 32, 28)
        form.setSpacing(18)

        self.mode = QComboBox()
        self.mode.addItem("Tự luyện – xem đáp án ngay", "practice")
        self.mode.addItem("Thi thử – chấm điểm cuối bài", "exam")
        self.question_count = QSpinBox()
        self.question_count.setRange(1, max(situation_count, 1))
        self.question_count.setValue(min(10, max(situation_count, 1)))
        self.difficulty = QComboBox()
        self.difficulty.addItem("Cơ bản – 2 đáp án", 2)
        self.difficulty.addItem("Tiêu chuẩn – 3 đáp án", 3)
        self.difficulty.addItem("Nâng cao – 4 đáp án", 4)
        self.difficulty.setCurrentIndex(1)

        form.addRow("Chế độ", self.mode)
        form.addRow("Số tình huống", self.question_count)
        form.addRow("Mức độ", self.difficulty)
        layout.addWidget(card)

        actions = QHBoxLayout()
        history = QPushButton("Lịch sử")
        history.setObjectName("secondaryButton")
        start = QPushButton("Bắt đầu")
        start.setObjectName("primaryButton")
        start.clicked.connect(self._emit_start)
        history.clicked.connect(self.history_requested.emit)
        actions.addStretch()
        actions.addWidget(history)
        actions.addWidget(start)
        layout.addLayout(actions)
        layout.addStretch()

    def _emit_start(self) -> None:
        self.start_requested.emit(
            str(self.mode.currentData()),
            self.question_count.value(),
            int(self.difficulty.currentData()),
        )


class SessionPage(QWidget):
    finished = Signal(float, int, int)
    exit_requested = Signal()

    def __init__(self, videos_directory: Path):
        super().__init__()
        self._videos_directory = videos_directory
        self._state: SessionState | None = None
        self._groups: dict[int, QButtonGroup] = {}
        self._answer_buttons: dict[int, QRadioButton] = {}
        self._checked = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.video.setMinimumSize(560, 360)
        self.player.setVideoOutput(self.video)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        header = QHBoxLayout()
        self.position_label = QLabel()
        self.position_label.setObjectName("sectionTitle")
        exit_button = QPushButton("Thoát")
        exit_button.setObjectName("dangerButton")
        exit_button.clicked.connect(self._confirm_exit)
        header.addWidget(self.position_label)
        header.addStretch()
        header.addWidget(exit_button)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(22)
        video_panel = QVBoxLayout()
        video_panel.addWidget(self.video, 1)
        self.video_status = QLabel()
        self.video_status.setWordWrap(True)
        self.video_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls = QHBoxLayout()
        play_pause = QPushButton("Phát / Tạm dừng")
        replay = QPushButton("Phát lại")
        play_pause.clicked.connect(self._toggle_playback)
        replay.clicked.connect(self._replay)
        controls.addWidget(play_pause)
        controls.addWidget(replay)
        video_panel.addWidget(self.video_status)
        video_panel.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.questions_host = QWidget()
        self.questions_layout = QVBoxLayout(self.questions_host)
        self.questions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.questions_host)

        body.addLayout(video_panel, 5)
        body.addWidget(self.scroll, 5)
        root.addLayout(body, 1)

        footer = QHBoxLayout()
        self.progress_label = QLabel()
        self.submit_button = QPushButton("Kiểm tra đáp án")
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.clicked.connect(self._submit)
        footer.addWidget(self.progress_label)
        footer.addStretch()
        footer.addWidget(self.submit_button)
        root.addLayout(footer)

    def begin(self, state: SessionState) -> None:
        self._state = state
        self._render_current()

    def _render_current(self) -> None:
        assert self._state is not None
        self._clear_questions()
        self._checked = False
        situation = self._state.current
        self.position_label.setText(
            f"{situation.code} · {situation.title}   "
            f"({self._state.current_index + 1}/{len(self._state.situations)})"
        )
        self.progress_label.setText(
            f"{situation.chapter} · Đã hoàn thành {len(self._state.results)}/{len(self._state.situations)}"
        )
        self.submit_button.setText(
            "Nộp câu trả lời" if self._state.mode == "exam" else "Kiểm tra đáp án"
        )

        for index, part in enumerate(situation.parts, start=1):
            box = QGroupBox(f"Phần {index}: {part.prompt}")
            box_layout = QVBoxLayout(box)
            group = QButtonGroup(box)
            group.setExclusive(True)
            self._groups[part.id] = group
            for answer_index, answer in enumerate(part.answers):
                label = chr(ord("A") + answer_index)
                button = QRadioButton(f"{label}. {answer.text}")
                button.setProperty("answerId", answer.id)
                group.addButton(button, answer.id)
                self._answer_buttons[answer.id] = button
                box_layout.addWidget(button)
            self.questions_layout.addWidget(box)

        self._load_video(situation)

    def _load_video(self, situation: Situation) -> None:
        video_path = situation.video_path(self._videos_directory)
        self.player.stop()
        if not video_path.is_file():
            self.player.setSource(QUrl())
            self.video_status.setText(f"Chưa có video: {video_path.name}")
            return
        self.video_status.setText(video_path.name)
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.player.play()

    def _selected_answers(self) -> dict[int, int]:
        selections: dict[int, int] = {}
        for part_id, group in self._groups.items():
            if group.checkedId() >= 0:
                selections[part_id] = group.checkedId()
        return selections

    def _submit(self) -> None:
        assert self._state is not None
        if self._checked:
            self._advance_or_finish()
            return

        selections = self._selected_answers()
        if len(selections) != len(self._groups):
            QMessageBox.information(self, "Chưa hoàn thành", "Hãy trả lời đủ cả bốn phần.")
            return

        result = self._state.submit_current(selections)
        if self._state.mode == "practice":
            self._show_feedback(result)
            self._checked = True
            self.submit_button.setText("Xem kết quả" if self._state.is_last else "Câu tiếp theo")
        else:
            self._advance_or_finish()

    def _show_feedback(self, result: SituationResult) -> None:
        for part in result.parts:
            selected = self._answer_buttons.get(part.selected_answer_id or -1)
            correct = self._answer_buttons.get(part.correct_answer_id)
            if correct:
                correct.setStyleSheet("color: #116329; font-weight: 700;")
            if selected and not part.is_correct:
                selected.setStyleSheet("color: #a32020; font-weight: 700;")
        self.progress_label.setText(f"Kết quả câu này: {result.correct_parts}/4 phần đúng")

    def _advance_or_finish(self) -> None:
        assert self._state is not None
        if self._state.move_next():
            self._render_current()
            return
        final_score = self._state.finish(self.window().history_repository)
        correct = sum(result.correct_parts for result in self._state.results)
        total = len(self._state.situations) * 4
        self.player.stop()
        self.finished.emit(final_score, correct, total)

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _replay(self) -> None:
        self.player.setPosition(0)
        self.player.play()

    def _confirm_exit(self) -> None:
        answer = QMessageBox.question(self, "Thoát phiên", "Bạn muốn thoát phiên hiện tại?")
        if answer == QMessageBox.StandardButton.Yes:
            self.player.stop()
            self.exit_requested.emit()

    def _clear_questions(self) -> None:
        self._groups.clear()
        self._answer_buttons.clear()
        while self.questions_layout.count():
            item = self.questions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ResultPage(QWidget):
    home_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score = QLabel()
        self.score.setObjectName("score")
        self.score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel()
        self.detail.setObjectName("subtitle")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home = QPushButton("Về trang thiết lập")
        home.setObjectName("primaryButton")
        home.clicked.connect(self.home_requested.emit)
        layout.addWidget(QLabel("KẾT QUẢ"), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score)
        layout.addWidget(self.detail)
        layout.addSpacing(24)
        layout.addWidget(home, alignment=Qt.AlignmentFlag.AlignCenter)

    def show_result(self, score: float, correct: int, total: int) -> None:
        self.score.setText(f"{score:.2f} / 10")
        self.detail.setText(f"Đúng {correct}/{total} phần")


class HistoryDialog(QDialog):
    def __init__(self, history_repository: HistoryRepository, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch sử luyện tập")
        self.resize(780, 440)
        layout = QVBoxLayout(self)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["Thời gian", "Chế độ", "Số câu", "Điểm", "Thang 10", "Trạng thái"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row_index, row in enumerate(history_repository.recent_sessions()):
            table.insertRow(row_index)
            values = [
                row["started_at"],
                "Tự luyện" if row["mode"] == "practice" else "Thi thử",
                row["total_situations"],
                "-" if row["score"] is None else row["score"],
                "-" if row["score_on_ten"] is None else row["score_on_ten"],
                "Hoàn thành" if row["completed_at"] else "Chưa hoàn thành",
            ]
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        layout.addWidget(table)


class MainWindow(QMainWindow):
    def __init__(
        self,
        content_repository: ContentRepository,
        history_repository: HistoryRepository,
        videos_directory: Path,
    ):
        super().__init__()
        self.content_repository = content_repository
        self.history_repository = history_repository
        self.setWindowTitle("Mô phỏng GPLX")
        self.resize(1366, 820)
        self.setMinimumSize(1100, 720)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.setup_page = SetupPage(content_repository.count_situations())
        self.session_page = SessionPage(videos_directory)
        self.result_page = ResultPage()
        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.session_page)
        self.stack.addWidget(self.result_page)

        self.setup_page.start_requested.connect(self._start_session)
        self.setup_page.history_requested.connect(self._show_history)
        self.session_page.finished.connect(self._show_result)
        self.session_page.exit_requested.connect(self._show_home)
        self.result_page.home_requested.connect(self._show_home)

    def _start_session(self, mode: str, count: int, answer_limit: int) -> None:
        try:
            situations = self.content_repository.get_random_situations(count, answer_limit)
        except (LookupError, ValueError) as error:
            QMessageBox.critical(self, "Lỗi dữ liệu", str(error))
            return
        if not situations:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Không tìm thấy tình huống đang hoạt động.")
            return
        session_id = self.history_repository.start_session(mode, situations)
        self.session_page.begin(SessionState(session_id, mode, situations))
        self.stack.setCurrentWidget(self.session_page)

    def _show_result(self, score: float, correct: int, total: int) -> None:
        self.result_page.show_result(score, correct, total)
        self.stack.setCurrentWidget(self.result_page)

    def _show_history(self) -> None:
        HistoryDialog(self.history_repository, self).exec()

    def _show_home(self) -> None:
        self.stack.setCurrentWidget(self.setup_page)

