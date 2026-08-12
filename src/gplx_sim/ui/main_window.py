from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
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
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
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


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class AnswerOption(QFrame):
    def __init__(self, label: str, text: str):
        super().__init__()
        self.setObjectName("answerOption")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 10, 7)
        layout.setSpacing(6)
        self.radio = QRadioButton()
        self.radio.setObjectName("answerRadio")
        self.radio.setFixedWidth(20)
        self.radio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio.toggled.connect(self._sync_selected_style)
        self.text_label = ClickableLabel(f"{label}. {text}")
        self.text_label.setObjectName("answerText")
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.text_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text_label.clicked.connect(self.radio.click)
        layout.addWidget(self.radio, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.text_label, 1)

    def _sync_selected_style(self, checked: bool) -> None:
        self.setProperty("selected", checked)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if self.isEnabled():
            self.radio.click()
        super().mousePressEvent(event)

    def show_feedback(self, is_correct: bool) -> None:
        color = "#116329" if is_correct else "#a32020"
        background = "#eaf7ee" if is_correct else "#fff0f0"
        border = "#8ac99b" if is_correct else "#e5aaaa"
        self.setStyleSheet(
            "QFrame#answerOption {"
            f"background: {background}; border: 1px solid {border}; border-radius: 6px;"
            "}"
            f"QLabel#answerText {{ color: {color}; font-weight: 700; background: transparent; }}"
        )


class HomePage(QWidget):
    study_requested = Signal()
    official_exam_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 54, 80, 54)
        layout.setSpacing(18)

        heading = QLabel("MÔ PHỎNG TÌNH HUỐNG GIAO THÔNG")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Chọn chức năng để bắt đầu")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        choices = QHBoxLayout()
        choices.setSpacing(28)
        choices.addWidget(
            self._choice_card(
                "ÔN TẬP",
                "Tự luyện có phản hồi ngay hoặc thi thử có giới hạn thời gian.",
                "Vào phần ôn tập",
                self.study_requested.emit,
                "studyCard",
            )
        )
        choices.addWidget(
            self._choice_card(
                "THI TỐT NGHIỆP",
                "Chọn khóa thi, kiểm tra thông tin thí sinh và thực hiện bài thi chính thức.",
                "Vào phần thi",
                self.official_exam_requested.emit,
                "examCard",
            )
        )
        layout.addLayout(choices, 1)
        note = QLabel("Dữ liệu câu hỏi và video được sử dụng trực tiếp trên máy này.")
        note.setObjectName("mutedText")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

    @staticmethod
    def _choice_card(title: str, description: str, button_text: str, callback, object_name: str):
        card = QFrame()
        card.setObjectName(object_name)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 38, 38, 38)
        card_layout.setSpacing(18)
        title_label = QLabel(title)
        title_label.setObjectName("choiceTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label = QLabel(description)
        description_label.setObjectName("choiceDescription")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        button = QPushButton(button_text)
        button.setObjectName("primaryButton")
        button.setMinimumHeight(54)
        button.clicked.connect(callback)
        card_layout.addStretch()
        card_layout.addWidget(title_label)
        card_layout.addWidget(description_label)
        card_layout.addSpacing(18)
        card_layout.addWidget(button)
        card_layout.addStretch()
        return card


class StudySetupPage(QWidget):
    start_requested = Signal(str, int, int)
    history_requested = Signal()
    home_requested = Signal()

    def __init__(self, situation_count: int):
        super().__init__()
        self._situation_count = max(situation_count, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 36, 64, 44)
        layout.setSpacing(20)

        top = QHBoxLayout()
        back = QPushButton("← Trang chủ")
        back.clicked.connect(self.home_requested.emit)
        history = QPushButton("Lịch sử ôn tập")
        history.clicked.connect(self.history_requested.emit)
        top.addWidget(back)
        top.addStretch()
        top.addWidget(history)
        layout.addLayout(top)

        heading = QLabel("ÔN TẬP")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Mỗi phần câu hỏi luôn hiển thị đầy đủ 4 phương án A–D")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("studySetupCard")
        card.setMinimumHeight(250)
        form = QFormLayout(card)
        form.setContentsMargins(38, 34, 38, 34)
        form.setVerticalSpacing(24)
        form.setHorizontalSpacing(24)

        self.mode = QComboBox()
        self.mode.addItem("Tự luyện – phản hồi đáp án ngay", "practice")
        self.mode.addItem("Thi thử – bấm giờ, không hiện đáp án", "mock_exam")
        self.mode.currentIndexChanged.connect(self._sync_mode_controls)

        self.question_count = QSpinBox()
        self.question_count.setRange(1, min(20, self._situation_count))
        self.question_count.setValue(min(10, self._situation_count))
        self.question_count.setSuffix(" tình huống")
        self.question_count.valueChanged.connect(self._sync_mode_controls)
        self.question_count_label = QLabel("Số tình huống")

        self.duration = QSpinBox()
        self.duration.setRange(1, 30)
        self.duration.setValue(15)
        self.duration.setSuffix(" phút")
        self.duration.valueChanged.connect(self._sync_mode_controls)
        self.duration_label = QLabel("Tổng thời gian")

        form.addRow("Chế độ", self.mode)
        form.addRow(self.question_count_label, self.question_count)
        form.addRow(self.duration_label, self.duration)
        layout.addWidget(card)

        self.summary = QLabel()
        self.summary.setObjectName("summaryBox")
        self.summary.setMinimumHeight(62)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        start = QPushButton("Bắt đầu ôn tập")
        start.setObjectName("primaryButton")
        start.setMinimumSize(280, 54)
        start.clicked.connect(self._emit_start)
        layout.addWidget(start, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self._sync_mode_controls()

    def _sync_mode_controls(self) -> None:
        is_mock_exam = self.mode.currentData() == "mock_exam"
        self.question_count.setEnabled(not is_mock_exam)
        if is_mock_exam:
            self.question_count.setValue(min(10, self._situation_count))
        self.duration.setVisible(is_mock_exam)
        self.duration_label.setVisible(is_mock_exam)
        if is_mock_exam:
            self.summary.setText(
                f"Thi thử gồm {self.question_count.value()} tình huống, thời gian "
                f"{self.duration.value()} phút. Không hiển thị đáp án trong lúc làm bài."
            )
        else:
            self.summary.setText(
                "Tự luyện phản hồi đúng/sai ngay sau mỗi tình huống và cho phép học viên "
                "so sánh với đáp án đúng."
            )

    def _emit_start(self) -> None:
        mode = str(self.mode.currentData())
        count = min(10, self._situation_count) if mode == "mock_exam" else self.question_count.value()
        duration_seconds = self.duration.value() * 60 if mode == "mock_exam" else 0
        self.start_requested.emit(mode, count, duration_seconds)


class OfficialExamPage(QWidget):
    home_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 36, 80, 52)
        layout.setSpacing(20)

        back = QPushButton("← Trang chủ")
        back.clicked.connect(self.home_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)
        heading = QLabel("THI TỐT NGHIỆP")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Kiểm tra thông tin thí sinh trước khi bắt đầu thi")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(subtitle)

        lookup_card = QFrame()
        lookup_card.setObjectName("card")
        lookup_form = QFormLayout(lookup_card)
        lookup_form.setContentsMargins(32, 28, 32, 28)
        lookup_form.setSpacing(18)
        self.course = QComboBox()
        self.course.addItem("Chưa kết nối máy chủ – chưa có khóa thi đang mở", None)
        self.candidate_number = QLineEdit()
        self.candidate_number.setPlaceholderText("Nhập số báo danh")
        self.candidate_number.setMaxLength(20)
        check_button = QPushButton("Kiểm tra thông tin")
        check_button.setObjectName("primaryButton")
        check_button.clicked.connect(self._check_information)
        lookup_form.addRow("Khóa thi đang thi", self.course)
        lookup_form.addRow("Số báo danh", self.candidate_number)
        lookup_form.addRow("", check_button)
        layout.addWidget(lookup_card)

        info = QGroupBox("Thông tin thí sinh")
        info_form = QFormLayout(info)
        self.info_labels: dict[str, QLabel] = {}
        for key, title in (
            ("candidate_number", "Số báo danh"),
            ("full_name", "Họ và tên"),
            ("date_of_birth", "Ngày sinh"),
            ("identity_number", "Số CCCD"),
            ("license_class", "Hạng thi"),
        ):
            value = QLabel("—")
            value.setObjectName("candidateValue")
            self.info_labels[key] = value
            info_form.addRow(title, value)
        layout.addWidget(info)

        status = QLabel(
            "Phần Thi tốt nghiệp đã được dựng giao diện. Danh sách khóa thi và dữ liệu "
            "thí sinh sẽ được nối với máy chủ ở giai đoạn tiếp theo."
        )
        status.setObjectName("noticeBox")
        status.setWordWrap(True)
        layout.addWidget(status)
        layout.addStretch()

    def _check_information(self) -> None:
        if not self.candidate_number.text().strip():
            QMessageBox.information(self, "Thiếu số báo danh", "Hãy nhập số báo danh cần kiểm tra.")
            return
        QMessageBox.information(
            self,
            "Chưa kết nối máy chủ",
            "Chức năng tra cứu khóa thi và thí sinh sẽ được phát triển ở giai đoạn tiếp theo.",
        )


class SessionPage(QWidget):
    finished = Signal(float, int, int, str, str)
    exit_requested = Signal()

    def __init__(self, videos_directory: Path):
        super().__init__()
        self._videos_directory = videos_directory
        self._state: SessionState | None = None
        self._groups: dict[int, QButtonGroup] = {}
        self._answer_options: dict[int, AnswerOption] = {}
        self._checked = False
        self._is_finished = False
        self._remaining_seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.video.setMinimumSize(520, 340)
        self.player.setVideoOutput(self.video)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        header = QHBoxLayout()
        self.position_label = QLabel()
        self.position_label.setObjectName("sectionTitle")
        self.timer_label = QLabel()
        self.timer_label.setObjectName("timerLabel")
        exit_button = QPushButton("Thoát")
        exit_button.setObjectName("dangerButton")
        exit_button.clicked.connect(self._confirm_exit)
        header.addWidget(self.position_label)
        header.addStretch()
        header.addWidget(self.timer_label)
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
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.questions_host = QWidget()
        self.questions_layout = QVBoxLayout(self.questions_host)
        self.questions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.questions_host)
        body.addLayout(video_panel, 6)
        body.addWidget(self.scroll, 4)
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

    def begin(self, state: SessionState, duration_seconds: int = 0) -> None:
        self._timer.stop()
        self._state = state
        self._is_finished = False
        self._remaining_seconds = duration_seconds
        self.timer_label.setVisible(state.mode == "mock_exam")
        if state.mode == "mock_exam":
            self._update_timer_label()
            self._timer.start()
        self._render_current()

    def _render_current(self) -> None:
        assert self._state is not None
        self._clear_questions()
        self._checked = False
        situation = self._state.current
        mode_name = "Thi thử" if self._state.mode == "mock_exam" else "Tự luyện"
        self.position_label.setText(
            f"{mode_name} · {situation.code} · {situation.title}   "
            f"({self._state.current_index + 1}/{len(self._state.situations)})"
        )
        self.progress_label.setText(
            f"{situation.chapter} · Đã hoàn thành {len(self._state.results)}/{len(self._state.situations)}"
        )
        self.submit_button.setText(
            "Nộp câu trả lời" if self._state.mode == "mock_exam" else "Kiểm tra đáp án"
        )

        for index, part in enumerate(situation.parts, start=1):
            box = QGroupBox(f"Phần {index}: {part.prompt}")
            box_layout = QVBoxLayout(box)
            group = QButtonGroup(box)
            group.setExclusive(True)
            self._groups[part.id] = group
            for answer_index, answer in enumerate(part.answers):
                label = chr(ord("A") + answer_index)
                option = AnswerOption(label, answer.text)
                group.addButton(option.radio, answer.id)
                self._answer_options[answer.id] = option
                box_layout.addWidget(option)
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
        return {
            part_id: group.checkedId()
            for part_id, group in self._groups.items()
            if group.checkedId() >= 0
        }

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
        for option in self._answer_options.values():
            option.setEnabled(False)
        for part in result.parts:
            selected = self._answer_options.get(part.selected_answer_id or -1)
            correct = self._answer_options.get(part.correct_answer_id)
            if correct:
                correct.show_feedback(True)
            if selected and not part.is_correct:
                selected.show_feedback(False)
        self.progress_label.setText(f"Kết quả câu này: {result.correct_parts}/4 phần đúng")

    def _advance_or_finish(self) -> None:
        assert self._state is not None
        if self._state.move_next():
            self._render_current()
        else:
            self._finish_session("Đã hoàn thành")

    def _finish_session(self, reason: str) -> None:
        if self._is_finished or self._state is None:
            return
        self._is_finished = True
        self._timer.stop()
        self.player.stop()
        final_score = self._state.finish(self.window().history_repository)
        correct = sum(result.correct_parts for result in self._state.results)
        total = len(self._state.situations) * 4
        self.finished.emit(final_score, correct, total, self._state.mode, reason)

    def _tick(self) -> None:
        self._remaining_seconds = max(0, self._remaining_seconds - 1)
        self._update_timer_label()
        if self._remaining_seconds == 0:
            self._timer.stop()
            QMessageBox.information(self, "Hết thời gian", "Bài thi thử sẽ được tự động nộp.")
            self._finish_session("Hết thời gian")

    def _update_timer_label(self) -> None:
        minutes, seconds = divmod(self._remaining_seconds, 60)
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        if self._remaining_seconds < 60:
            color = "#c92a2a"
        elif self._remaining_seconds <= 300:
            color = "#d97706"
        else:
            color = "#1769aa"
        self.timer_label.setStyleSheet(f"color: {color};")

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
            self._timer.stop()
            self.player.stop()
            self.exit_requested.emit()

    def _clear_questions(self) -> None:
        self._groups.clear()
        self._answer_options.clear()
        while self.questions_layout.count():
            item = self.questions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ResultPage(QWidget):
    setup_requested = Signal()
    home_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel("KẾT QUẢ")
        self.title.setObjectName("heading")
        self.score = QLabel()
        self.score.setObjectName("score")
        self.score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel()
        self.detail.setObjectName("subtitle")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions = QHBoxLayout()
        home = QPushButton("Trang chủ")
        home.clicked.connect(self.home_requested.emit)
        setup = QPushButton("Ôn tập tiếp")
        setup.setObjectName("primaryButton")
        setup.clicked.connect(self.setup_requested.emit)
        actions.addWidget(home)
        actions.addWidget(setup)
        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score)
        layout.addWidget(self.detail)
        layout.addSpacing(24)
        layout.addLayout(actions)

    def show_result(self, score: float, correct: int, total: int, mode: str, reason: str) -> None:
        self.title.setText("KẾT QUẢ THI THỬ" if mode == "mock_exam" else "KẾT QUẢ TỰ LUYỆN")
        self.score.setText(f"{score:.2f} / 10")
        self.detail.setText(f"Đúng {correct}/{total} phần · {reason}")


class HistoryDialog(QDialog):
    def __init__(self, history_repository: HistoryRepository, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch sử ôn tập")
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
        self.home_page = HomePage()
        self.study_setup_page = StudySetupPage(content_repository.count_situations())
        self.official_exam_page = OfficialExamPage()
        self.session_page = SessionPage(videos_directory)
        self.result_page = ResultPage()
        for page in (
            self.home_page,
            self.study_setup_page,
            self.official_exam_page,
            self.session_page,
            self.result_page,
        ):
            self.stack.addWidget(page)

        self.home_page.study_requested.connect(self._show_study_setup)
        self.home_page.official_exam_requested.connect(self._show_official_exam)
        self.study_setup_page.start_requested.connect(self._start_study_session)
        self.study_setup_page.history_requested.connect(self._show_history)
        self.study_setup_page.home_requested.connect(self._show_home)
        self.official_exam_page.home_requested.connect(self._show_home)
        self.session_page.finished.connect(self._show_result)
        self.session_page.exit_requested.connect(self._show_study_setup)
        self.result_page.setup_requested.connect(self._show_study_setup)
        self.result_page.home_requested.connect(self._show_home)
        self._show_home()

    def _start_study_session(self, mode: str, count: int, duration_seconds: int) -> None:
        try:
            situations = self.content_repository.get_random_situations(count)
        except (LookupError, ValueError) as error:
            QMessageBox.critical(self, "Lỗi dữ liệu", str(error))
            return
        if not situations:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Không tìm thấy tình huống đang hoạt động.")
            return
        session_id = self.history_repository.start_session(mode, situations)
        self.session_page.begin(
            SessionState(session_id=session_id, mode=mode, situations=situations),
            duration_seconds,
        )
        self.stack.setCurrentWidget(self.session_page)

    def _show_result(
        self, score: float, correct: int, total: int, mode: str, reason: str
    ) -> None:
        self.result_page.show_result(score, correct, total, mode, reason)
        self.stack.setCurrentWidget(self.result_page)

    def _show_history(self) -> None:
        HistoryDialog(self.history_repository, self).exec()

    def _show_home(self) -> None:
        self.stack.setCurrentWidget(self.home_page)

    def _show_study_setup(self) -> None:
        self.stack.setCurrentWidget(self.study_setup_page)

    def _show_official_exam(self) -> None:
        self.stack.setCurrentWidget(self.official_exam_page)
