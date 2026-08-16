from __future__ import annotations

import unicodedata
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QSlider,
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


class SourceOption(QFrame):
    def __init__(self, title: str, description: str):
        super().__init__()
        self.setObjectName("sourceOption")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        self.radio = QRadioButton()
        self.radio.setObjectName("sourceRadio")
        self.radio.setCursor(Qt.CursorShape.PointingHandCursor)
        labels = QVBoxLayout()
        labels.setSpacing(3)
        title_label = ClickableLabel(title)
        title_label.setObjectName("sourceTitle")
        description_label = ClickableLabel(description)
        description_label.setObjectName("sourceDescription")
        description_label.setWordWrap(True)
        for label in (title_label, description_label):
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.clicked.connect(self.radio.click)
        labels.addWidget(title_label)
        labels.addWidget(description_label)
        layout.addWidget(self.radio, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(labels, 1)
        self.radio.toggled.connect(self._sync_selected_style)

    def _sync_selected_style(self, checked: bool) -> None:
        self.setProperty("selected", checked)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if self.isEnabled():
            self.radio.click()
        super().mousePressEvent(event)


class SituationCountSelector(QWidget):
    valueChanged = Signal(int)

    def __init__(self, maximum: int):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.minus = QPushButton("−")
        self.minus.setObjectName("stepButton")
        self.minus.setToolTip("Giảm một tình huống")
        self.value_box = QSpinBox()
        self.value_box.setObjectName("countValue")
        self.value_box.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.value_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_box.setRange(1, max(1, maximum))
        self.value_box.setValue(min(10, maximum))
        self.value_box.setSuffix(" tình huống")
        self.plus = QPushButton("+")
        self.plus.setObjectName("stepButton")
        self.plus.setToolTip("Tăng một tình huống")
        for button in (self.minus, self.plus):
            button.setFixedSize(48, 48)
            button.setAutoRepeat(True)
        self.minus.clicked.connect(self.value_box.stepDown)
        self.plus.clicked.connect(self.value_box.stepUp)
        self.value_box.valueChanged.connect(self._value_changed)
        layout.addWidget(self.minus)
        layout.addWidget(self.value_box, 1)
        layout.addWidget(self.plus)
        self._value_changed(self.value_box.value())

    def value(self) -> int:
        return self.value_box.value()

    def _value_changed(self, value: int) -> None:
        self.minus.setEnabled(value > self.value_box.minimum())
        self.plus.setEnabled(value < self.value_box.maximum())
        self.valueChanged.emit(value)


class SituationSelectionDialog(QDialog):
    def __init__(
        self,
        repository: ContentRepository,
        selected_ids: set[int] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Chọn tình huống tự luyện")
        self.resize(1100, 720)
        self._situations = repository.list_situations()
        self._selected_ids = set(selected_ids or set())
        self._selection_boxes: dict[int, QPushButton] = {}
        self._checked_icon = self._create_checked_icon()
        self._updating_table = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        heading = QLabel("CHỌN TÌNH HUỐNG TỰ LUYỆN")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm theo mã hoặc tên tình huống...")
        self.chapter = QComboBox()
        self.chapter.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.chapter.setMinimumContentsLength(24)
        self.chapter.addItem("Tất cả chương", None)
        for chapter in repository.list_chapters():
            self.chapter.addItem(f"Chương {chapter.id} – {chapter.name}", chapter.id)
        filters.addWidget(self.search, 2)
        filters.addWidget(self.chapter, 3)
        root.addLayout(filters)

        selection_hint = QLabel(
            "Tích vào ô Chọn hoặc bấm vào bất kỳ vị trí nào trên hàng để chọn tình huống."
        )
        selection_hint.setObjectName("selectionHint")
        root.addWidget(selection_hint)

        self.table = QTableWidget(len(self._situations), 5)
        self.table.setHorizontalHeaderLabels(["Chọn", "Mã", "Chương", "Tên tình huống", "Video"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        for column in (0, 1, 2, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for row, situation in enumerate(self._situations):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            check_item.setData(Qt.ItemDataRole.UserRole, situation.id)
            self.table.setItem(row, 0, check_item)
            check_host = QWidget()
            check_host.setObjectName("situationCheckHost")
            check_layout = QHBoxLayout(check_host)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_button = QPushButton()
            check_button.setObjectName("situationCheckBox")
            check_button.setCheckable(True)
            check_button.setChecked(situation.id in self._selected_ids)
            check_button.setIcon(
                self._checked_icon if check_button.isChecked() else QIcon()
            )
            check_button.setIconSize(QSize(18, 18))
            check_button.setToolTip(f"Chọn {situation.code}")
            check_button.toggled.connect(
                lambda checked, button=check_button, situation_id=situation.id: self._selection_toggled(
                    button, situation_id, checked
                )
            )
            self._selection_boxes[situation.id] = check_button
            check_layout.addWidget(check_button, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 0, check_host)
            self.table.setItem(row, 1, QTableWidgetItem(situation.code))
            self.table.setItem(row, 2, QTableWidgetItem(f"Chương {situation.chapter_id}"))
            self.table.setItem(row, 3, QTableWidgetItem(situation.title))
            self.table.setItem(row, 4, QTableWidgetItem(situation.video_filename))
        root.addWidget(self.table, 1)

        selection_actions = QHBoxLayout()
        self.selected_count = QLabel()
        self.selected_count.setObjectName("selectedCount")
        select_visible = QPushButton("Chọn phần đang hiển thị")
        clear_visible = QPushButton("Bỏ chọn phần đang hiển thị")
        select_visible.clicked.connect(lambda: self._set_visible_rows(True))
        clear_visible.clicked.connect(lambda: self._set_visible_rows(False))
        selection_actions.addWidget(self.selected_count)
        selection_actions.addStretch()
        selection_actions.addWidget(select_visible)
        selection_actions.addWidget(clear_visible)
        root.addLayout(selection_actions)

        actions = QHBoxLayout()
        cancel = QPushButton("Hủy")
        cancel.clicked.connect(self.reject)
        self.use_selected = QPushButton("Dùng các tình huống đã chọn")
        self.use_selected.setObjectName("primaryButton")
        self.use_selected.clicked.connect(self.accept)
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(self.use_selected)
        root.addLayout(actions)

        self.search.textChanged.connect(self._apply_filters)
        self.chapter.currentIndexChanged.connect(self._apply_filters)
        self.table.cellClicked.connect(self._row_clicked)
        self._update_selected_count()

    @property
    def selected_ids(self) -> list[int]:
        return sorted(self._selected_ids)

    @staticmethod
    def _create_checked_icon() -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ffffff"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(3, 9, 7, 13)
        painter.drawLine(7, 13, 15, 4)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _search_key(value: str) -> str:
        decomposed = unicodedata.normalize("NFD", value)
        return "".join(character for character in decomposed if not unicodedata.combining(character)).casefold()

    def _apply_filters(self) -> None:
        query = self._search_key(self.search.text().strip())
        chapter_id = self.chapter.currentData()
        for row, situation in enumerate(self._situations):
            searchable = self._search_key(f"{situation.code} {situation.title}")
            visible = (not query or query in searchable) and (
                chapter_id is None or situation.chapter_id == chapter_id
            )
            self.table.setRowHidden(row, not visible)

    def _selection_toggled(
        self,
        button: QPushButton,
        situation_id: int,
        checked: bool,
    ) -> None:
        button.setIcon(self._checked_icon if checked else QIcon())
        if self._updating_table:
            return
        if checked:
            self._selected_ids.add(situation_id)
        else:
            self._selected_ids.discard(situation_id)
        self._update_selected_count()

    def _row_clicked(self, row: int, column: int) -> None:
        if column == 0:
            return
        situation_id = int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        check_button = self._selection_boxes[situation_id]
        check_button.setChecked(not check_button.isChecked())

    def _set_visible_rows(self, checked: bool) -> None:
        self._updating_table = True
        try:
            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                situation_id = int(
                    self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                )
                self._selection_boxes[situation_id].setChecked(checked)
                if checked:
                    self._selected_ids.add(situation_id)
                else:
                    self._selected_ids.discard(situation_id)
        finally:
            self._updating_table = False
        self._update_selected_count()

    def _update_selected_count(self) -> None:
        count = len(self._selected_ids)
        self.selected_count.setText(f"Đã chọn: {count}/120")
        self.use_selected.setEnabled(count > 0)


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
    start_requested = Signal(str, str, object, int)
    history_requested = Signal()
    home_requested = Signal()

    def __init__(self, content_repository: ContentRepository):
        super().__init__()
        self._repository = content_repository
        self._situation_count = max(content_repository.count_situations(), 1)
        self._custom_situation_ids: set[int] = set()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 28, 64, 36)
        layout.setSpacing(16)

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
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 26, 32, 26)
        card_layout.setSpacing(16)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Chế độ")
        mode_label.setObjectName("fieldLabel")
        self.mode = QComboBox()
        self.mode.addItem("Tự luyện – phản hồi đáp án ngay", "practice")
        self.mode.addItem("Thi thử – bấm giờ, không hiện đáp án", "mock_exam")
        self.mode.currentIndexChanged.connect(self._sync_mode_controls)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode, 1)
        card_layout.addLayout(mode_row)

        self.content_title = QLabel("Nội dung")
        self.content_title.setObjectName("fieldTitle")
        card_layout.addWidget(self.content_title)

        self.source_container = QWidget()
        source_layout = QHBoxLayout(self.source_container)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(12)
        self.source_group = QButtonGroup(self)
        self.source_group.setExclusive(True)
        self.random_source = SourceOption("Ngẫu nhiên", "Trộn câu từ 120 tình huống")
        self.set_source = SourceOption("Thi theo bộ đề", "Tối đa 10 tình huống do Admin chuẩn bị")
        self.custom_source = SourceOption("Tự chọn", "Lọc theo chương hoặc tìm kiếm")
        for identifier, option in enumerate(
            (self.random_source, self.set_source, self.custom_source)
        ):
            self.source_group.addButton(option.radio, identifier)
            option.radio.toggled.connect(self._sync_mode_controls)
            source_layout.addWidget(option, 1)
        card_layout.addWidget(self.source_container)

        self.random_row = QWidget()
        random_layout = QHBoxLayout(self.random_row)
        random_layout.setContentsMargins(0, 0, 0, 0)
        random_label = QLabel("Số tình huống")
        random_label.setObjectName("fieldLabel")
        self.question_count = SituationCountSelector(min(15, self._situation_count))
        self.question_count.valueChanged.connect(self._sync_mode_controls)
        random_layout.addWidget(random_label)
        random_layout.addWidget(self.question_count, 1)
        card_layout.addWidget(self.random_row)

        self.practice_set_row = QWidget()
        set_layout = QHBoxLayout(self.practice_set_row)
        set_layout.setContentsMargins(0, 0, 0, 0)
        set_label = QLabel("Bộ đề")
        set_label.setObjectName("fieldLabel")
        self.practice_set = QComboBox()
        self.practice_set.currentIndexChanged.connect(self._sync_mode_controls)
        set_layout.addWidget(set_label)
        set_layout.addWidget(self.practice_set, 1)
        card_layout.addWidget(self.practice_set_row)

        self.custom_row = QWidget()
        custom_layout = QHBoxLayout(self.custom_row)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_label = QLabel("Danh sách tình huống")
        custom_label.setObjectName("fieldLabel")
        self.custom_button = QPushButton("Mở danh sách 120 tình huống")
        self.custom_button.setObjectName("secondaryActionButton")
        self.custom_button.clicked.connect(self._choose_custom_situations)
        self.custom_count = QLabel("Chưa chọn tình huống")
        self.custom_count.setObjectName("mutedText")
        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(self.custom_button)
        custom_layout.addWidget(self.custom_count)
        custom_layout.addStretch()
        card_layout.addWidget(self.custom_row)

        self.duration = QSpinBox()
        self.duration.setRange(1, 30)
        self.duration.setValue(15)
        self.duration.setSuffix(" phút")
        self.duration.valueChanged.connect(self._sync_mode_controls)
        self.duration_row = QWidget()
        duration_layout = QHBoxLayout(self.duration_row)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_label = QLabel("Tổng thời gian")
        duration_label.setObjectName("fieldLabel")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration, 1)
        card_layout.addWidget(self.duration_row)
        layout.addWidget(card)

        self.summary = QLabel()
        self.summary.setObjectName("summaryBox")
        self.summary.setMinimumHeight(62)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.start = QPushButton("Bắt đầu ôn tập")
        self.start.setObjectName("primaryButton")
        self.start.setMinimumSize(280, 54)
        self.start.clicked.connect(self._emit_start)
        layout.addWidget(self.start, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.random_source.radio.setChecked(True)
        self.refresh_content_options()
        self._sync_mode_controls()

    def refresh_content_options(self) -> None:
        selected_set_id = self.practice_set.currentData()
        self.practice_set.blockSignals(True)
        self.practice_set.clear()
        practice_sets = self._repository.list_practice_sets()
        if practice_sets:
            for practice_set in practice_sets:
                self.practice_set.addItem(
                    f"{practice_set.code} – {practice_set.name} "
                    f"({practice_set.situation_count} tình huống)",
                    practice_set.id,
                )
            matching_index = self.practice_set.findData(selected_set_id)
            if matching_index >= 0:
                self.practice_set.setCurrentIndex(matching_index)
            self.practice_set.setEnabled(True)
        else:
            self.practice_set.addItem("Chưa có bộ đề – hãy tạo trong phần Admin", None)
            self.practice_set.setEnabled(False)
        self.practice_set.blockSignals(False)
        self._sync_mode_controls()

    def _selected_source(self) -> str:
        if self.set_source.radio.isChecked():
            return "practice_set"
        if self.custom_source.radio.isChecked():
            return "custom"
        return "random"

    def _sync_mode_controls(self) -> None:
        is_mock_exam = self.mode.currentData() == "mock_exam"
        source = self._selected_source()
        self.content_title.setVisible(not is_mock_exam)
        self.source_container.setVisible(not is_mock_exam)
        self.random_row.setVisible(not is_mock_exam and source == "random")
        self.practice_set_row.setVisible(not is_mock_exam and source == "practice_set")
        self.custom_row.setVisible(not is_mock_exam and source == "custom")
        self.duration_row.setVisible(is_mock_exam)
        if is_mock_exam:
            self.summary.setText(
                f"Thi thử gồm {min(10, self._situation_count)} tình huống ngẫu nhiên, thời gian "
                f"{self.duration.value()} phút. Không hiển thị đáp án trong lúc làm bài."
            )
            self.start.setText("Bắt đầu thi thử")
        elif source == "random":
            self.summary.setText(
                f"Tự luyện ngẫu nhiên {self.question_count.value()} tình huống và phản hồi "
                "đúng/sai ngay sau mỗi tình huống."
            )
            self.start.setText("Bắt đầu tự luyện")
        elif source == "practice_set":
            if self.practice_set.currentData() is None:
                self.summary.setText(
                    "Chưa có bộ đề đang hoạt động. Admin cần tạo bộ đề gồm tối đa 10 tình huống."
                )
            else:
                self.summary.setText(
                    "Luyện theo bộ đề đã được Admin chuẩn bị; thứ tự tình huống được giữ nguyên."
                )
            self.start.setText("Bắt đầu theo bộ đề")
        else:
            self.summary.setText(
                f"Đã chọn {len(self._custom_situation_ids)} tình huống. Có thể tìm kiếm, "
                "lọc theo chương và chọn bất kỳ tình huống nào cần luyện."
            )
            self.start.setText("Bắt đầu với danh sách đã chọn")

    def _choose_custom_situations(self) -> None:
        dialog = SituationSelectionDialog(
            self._repository,
            self._custom_situation_ids,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._custom_situation_ids = set(dialog.selected_ids)
        count = len(self._custom_situation_ids)
        self.custom_count.setText(f"Đã chọn {count}/120")
        self.custom_button.setText("Thay đổi danh sách")
        self._sync_mode_controls()

    def _emit_start(self) -> None:
        mode = str(self.mode.currentData())
        if mode == "mock_exam":
            self.start_requested.emit(
                mode,
                "random",
                min(10, self._situation_count),
                self.duration.value() * 60,
            )
            return

        source = self._selected_source()
        if source == "practice_set":
            practice_set_id = self.practice_set.currentData()
            if practice_set_id is None:
                QMessageBox.information(
                    self,
                    "Chưa có bộ đề",
                    "Admin chưa tạo bộ đề đang hoạt động.",
                )
                return
            selection: object = int(practice_set_id)
        elif source == "custom":
            if not self._custom_situation_ids:
                QMessageBox.information(
                    self,
                    "Chưa chọn tình huống",
                    "Hãy mở danh sách và chọn ít nhất một tình huống.",
                )
                return
            selection = sorted(self._custom_situation_ids)
        else:
            selection = self.question_count.value()
        self.start_requested.emit(mode, source, selection, 0)


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
        self._quick_buttons: list[QPushButton] = []
        self._draft_selections: dict[int, dict[int, int]] = {}
        self._checked = False
        self._is_finished = False
        self._video_available = False
        self._video_duration_ms = 0
        self._remaining_seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self._update_video_position)
        self.player.durationChanged.connect(self._update_video_duration)
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

        quick_row = QHBoxLayout()
        quick_label = QLabel("Chuyển nhanh")
        quick_label.setObjectName("quickNavLabel")
        self.quick_scroll = QScrollArea()
        self.quick_scroll.setObjectName("quickNavScroll")
        self.quick_scroll.setWidgetResizable(True)
        self.quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.quick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.quick_scroll.setMaximumHeight(58)
        self.quick_host = QWidget()
        self.quick_host.setObjectName("quickNavHost")
        self.quick_layout = QHBoxLayout(self.quick_host)
        self.quick_layout.setContentsMargins(2, 2, 2, 2)
        self.quick_layout.setSpacing(7)
        self.quick_scroll.setWidget(self.quick_host)
        quick_row.addWidget(quick_label)
        quick_row.addWidget(self.quick_scroll, 1)
        root.addLayout(quick_row)

        body = QHBoxLayout()
        body.setSpacing(22)
        video_panel = QVBoxLayout()
        video_panel.addWidget(self.video, 1)
        timeline = QHBoxLayout()
        self.video_slider = QSlider(Qt.Orientation.Horizontal)
        self.video_slider.setObjectName("videoTimeline")
        self.video_slider.setRange(0, 0)
        self.video_slider.sliderMoved.connect(self.player.setPosition)
        self.video_time_label = QLabel("00:00 / 00:00")
        self.video_time_label.setObjectName("videoTimeLabel")
        timeline.addWidget(self.video_slider, 1)
        timeline.addWidget(self.video_time_label)
        controls = QHBoxLayout()
        play_pause = QPushButton("Phát / Tạm dừng")
        replay = QPushButton("Phát lại")
        play_pause.clicked.connect(self._toggle_playback)
        replay.clicked.connect(self._replay)
        controls.addWidget(play_pause)
        controls.addWidget(replay)
        video_panel.addLayout(timeline)
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
        self._draft_selections.clear()
        self._is_finished = False
        self._remaining_seconds = duration_seconds
        self._build_quick_navigation()
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
        self.position_label.setText(f"{mode_name} · Tình huống số {situation.id}")
        self._update_progress_label()
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

        existing_result = self._result_for_situation(situation.id)
        saved_selections = (
            {
                part.part_id: part.selected_answer_id
                for part in existing_result.parts
                if part.selected_answer_id is not None
            }
            if existing_result is not None
            else self._draft_selections.get(situation.id, {})
        )
        for part_id, answer_id in saved_selections.items():
            group = self._groups.get(part_id)
            if group is not None:
                button = group.button(answer_id)
                if button is not None:
                    button.setChecked(True)

        if existing_result is not None and self._state.mode == "practice":
            self._show_feedback(existing_result)
            self._checked = True
            self.submit_button.setText(
                "Xem kết quả"
                if len(self._state.results) == len(self._state.situations)
                else "Câu tiếp theo"
            )
        self._load_video(situation)
        self._update_quick_navigation()

    def _load_video(self, situation: Situation) -> None:
        video_path = situation.video_path(self._videos_directory)
        self._video_available = False
        self._video_duration_ms = 0
        self.player.stop()
        self.video_slider.setRange(0, 0)
        self.video_slider.setValue(0)
        if not video_path.is_file():
            self.player.setSource(QUrl())
            self.video_slider.setEnabled(False)
            self.video_time_label.setText("Chưa có video")
            return
        self._video_available = True
        self.video_slider.setEnabled(True)
        self.video_time_label.setText("00:00 / 00:00")
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.player.play()

    @staticmethod
    def _format_media_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds // 1000)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _update_video_duration(self, duration: int) -> None:
        if not self._video_available:
            return
        self._video_duration_ms = max(0, duration)
        self.video_slider.setRange(0, max(0, duration))
        self._update_video_position(self.player.position())

    def _update_video_position(self, position: int) -> None:
        if not self._video_available:
            return
        if not self.video_slider.isSliderDown():
            self.video_slider.setValue(position)
        self.video_time_label.setText(
            f"{self._format_media_time(position)} / "
            f"{self._format_media_time(self._video_duration_ms)}"
        )

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
        self._draft_selections.pop(self._state.current.id, None)
        self._update_quick_navigation()
        self._update_progress_label()
        if self._state.mode == "practice":
            self._show_feedback(result)
            self._checked = True
            self.submit_button.setText(
                "Xem kết quả"
                if len(self._state.results) == len(self._state.situations)
                else "Câu tiếp theo"
            )
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
        self._update_progress_label(f"Kết quả: {result.correct_parts}/4 phần đúng")

    def _advance_or_finish(self) -> None:
        assert self._state is not None
        if len(self._state.results) == len(self._state.situations):
            self._finish_session("Đã hoàn thành")
            return
        completed_ids = {result.situation_id for result in self._state.results}
        total = len(self._state.situations)
        for offset in range(1, total + 1):
            index = (self._state.current_index + offset) % total
            if self._state.situations[index].id not in completed_ids:
                self._state.move_to(index)
                self._render_current()
                return

    def _build_quick_navigation(self) -> None:
        assert self._state is not None
        self._quick_buttons.clear()
        while self.quick_layout.count():
            item = self.quick_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index in range(len(self._state.situations)):
            button = QPushButton(str(index + 1))
            button.setObjectName("quickNavButton")
            button.setFixedSize(44, 40)
            button.setToolTip(f"Đi đến câu {index + 1}")
            button.clicked.connect(
                lambda checked=False, target_index=index: self._go_to_situation(target_index)
            )
            self._quick_buttons.append(button)
            self.quick_layout.addWidget(button)
        self.quick_layout.addStretch()

    def _go_to_situation(self, index: int) -> None:
        if self._state is None or index == self._state.current_index:
            return
        self._remember_current_selections()
        self._state.move_to(index)
        self._render_current()

    def _remember_current_selections(self) -> None:
        if self._state is None or self._checked:
            return
        selections = self._selected_answers()
        if selections:
            self._draft_selections[self._state.current.id] = selections
        else:
            self._draft_selections.pop(self._state.current.id, None)

    def _result_for_situation(self, situation_id: int) -> SituationResult | None:
        if self._state is None:
            return None
        return next(
            (result for result in self._state.results if result.situation_id == situation_id),
            None,
        )

    def _update_quick_navigation(self) -> None:
        if self._state is None:
            return
        results = {result.situation_id: result for result in self._state.results}
        for index, button in enumerate(self._quick_buttons):
            situation = self._state.situations[index]
            result = results.get(situation.id)
            if result is None:
                status = "pending"
            elif self._state.mode == "mock_exam":
                status = "answered"
            elif result.correct_parts == len(result.parts):
                status = "correct"
            else:
                status = "incorrect"
            button.setProperty("status", status)
            button.setProperty("current", index == self._state.current_index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _update_progress_label(self, detail: str = "") -> None:
        if self._state is None:
            return
        current = self._state.current_index + 1
        total = len(self._state.situations)
        text = f"Đang ở câu {current}/{total} · Đã hoàn thành {len(self._state.results)}/{total}"
        if detail:
            text += f" · {detail}"
        self.progress_label.setText(text)

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
        self.study_setup_page = StudySetupPage(content_repository)
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

    def _start_study_session(
        self,
        mode: str,
        source: str,
        selection: object,
        duration_seconds: int,
    ) -> None:
        try:
            if source == "practice_set":
                situations = self.content_repository.get_practice_set_situations(int(selection))
            elif source == "custom":
                situations = self.content_repository.get_situations_by_ids(
                    [int(identifier) for identifier in selection]
                )
            else:
                situations = self.content_repository.get_random_situations(int(selection))
        except (LookupError, TypeError, ValueError) as error:
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
        self.study_setup_page.refresh_content_options()
        self.stack.setCurrentWidget(self.study_setup_page)

    def _show_official_exam(self) -> None:
        self.stack.setCurrentWidget(self.official_exam_page)
