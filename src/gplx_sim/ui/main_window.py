from __future__ import annotations

import unicodedata
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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

    def __init__(
        self,
        maximum: int,
        *,
        minimum: int = 1,
        default: int = 10,
        suffix: str = " tình huống",
    ):
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
        self.value_box.setReadOnly(True)
        self.value_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.value_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upper_bound = max(minimum, maximum)
        self.value_box.setRange(minimum, upper_bound)
        self.value_box.setValue(min(max(default, minimum), upper_bound))
        self.value_box.setSuffix(suffix)
        self.plus = QPushButton("+")
        self.plus.setObjectName("stepButton")
        self.plus.setToolTip("Tăng một tình huống")
        for button in (self.minus, self.plus):
            button.setFixedSize(48, 48)
            button.setAutoRepeat(True)
        self.minus.clicked.connect(lambda: self._step_value(-1))
        self.plus.clicked.connect(lambda: self._step_value(1))
        self.value_box.valueChanged.connect(self._value_changed)
        layout.addWidget(self.minus)
        layout.addWidget(self.value_box, 1)
        layout.addWidget(self.plus)
        self._value_changed(self.value_box.value())

    def value(self) -> int:
        return self.value_box.value()

    def _step_value(self, offset: int) -> None:
        self.value_box.setValue(self.value_box.value() + offset)
        self.value_box.lineEdit().deselect()

    def _value_changed(self, value: int) -> None:
        self.minus.setEnabled(value > self.value_box.minimum())
        self.plus.setEnabled(value < self.value_box.maximum())
        self.value_box.lineEdit().deselect()
        self.valueChanged.emit(value)


class SituationCheckButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setObjectName("situationCheckBox")
        self.setCheckable(True)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = self.rect().adjusted(1, 1, -1, -1)
        if self.isChecked():
            background = QColor("#1769aa")
            border = QColor("#0f568f")
        elif self.underMouse():
            background = QColor("#eaf4ff")
            border = QColor("#1769aa")
        else:
            background = QColor("#ffffff")
            border = QColor("#607d9b")
        painter.setBrush(background)
        painter.setPen(QPen(border, 1.2))
        painter.drawRoundedRect(box, 3, 3)
        if self.isChecked():
            pen = QPen(QColor("#ffffff"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(3, 8, 6, 11)
            painter.drawLine(6, 11, 12, 4)
        painter.end()


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
            check_button = SituationCheckButton()
            check_button.setChecked(situation.id in self._selected_ids)
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
        button.update()
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


class AnimatedStackedWidget(QStackedWidget):
    """StackedWidget that switches pages without animation."""

    def slide_to_index(self, index: int, direction: str = "left") -> None:
        """Switch to page at index without animation."""
        if index == self.currentIndex():
            return
        self.setCurrentIndex(index)


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
        layout.addWidget(heading)
        layout.addSpacing(28)

        choices = QHBoxLayout()
        choices.setSpacing(28)
        choices.addWidget(
            self._choice_card(
                "ÔN TẬP",
                self.study_requested.emit,
                "studyCard",
            )
        )
        choices.addWidget(
            self._choice_card(
                "KIỂM TRA KẾT THÚC MÔN",
                self.official_exam_requested.emit,
                "examCard",
            )
        )
        layout.addLayout(choices, 1)

    def _choice_card(self, title: str, callback, object_name: str):
        card = _ClickableFrame()
        card.setObjectName(object_name)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.clicked.connect(callback)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 38, 38, 38)
        card_layout.setSpacing(18)
        title_label = QLabel(title)
        title_label.setObjectName("choiceTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addStretch()
        card_layout.addWidget(title_label)
        card_layout.addStretch()
        return card


class _ClickableFrame(QFrame):
    """A frame that can handle click events."""
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class StudySetupPage(QWidget):
    """Single page for study setup with 3 mode options: Ngẫu nhiên, Tự chọn, Thi thử."""

    start_requested = Signal(str, str, object, int)
    history_requested = Signal()
    home_requested = Signal()

    def __init__(self, content_repository: ContentRepository):
        super().__init__()
        self._repository = content_repository
        self._custom_situation_ids: set[int] = set()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(64, 28, 64, 36)
        layout.setSpacing(16)

        # Header
        top = QHBoxLayout()
        back = QPushButton("← Trang chủ")
        back.setObjectName("ghostButton")
        back.setMinimumHeight(36)
        back.clicked.connect(self.home_requested.emit)
        history = QPushButton("Lịch sử")
        history.setObjectName("ghostButton")
        history.setMinimumHeight(36)
        history.clicked.connect(self.history_requested.emit)
        top.addWidget(back)
        top.addStretch()
        top.addWidget(history)
        layout.addLayout(top)

        # Title
        heading = QLabel("ÔN TẬP")
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        # Main card with 3 options
        card = QFrame()
        card.setObjectName("studySetupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 26, 32, 26)
        card_layout.setSpacing(18)

        # Option group
        self.option_group = QButtonGroup(self)
        self.option_group.setExclusive(True)

        # Option 1: Ngẫu nhiên
        self.option_random = SourceOption(
            "Ngẫu nhiên",
            "10 tình huống theo cấu trúc chuẩn đề thi",
        )
        self.option_group.addButton(self.option_random.radio, 0)

        # Option 2: Tự chọn
        self.option_custom = SourceOption("Tự chọn", "Lọc theo chương hoặc tìm kiếm")
        self.option_group.addButton(self.option_custom.radio, 1)

        # Option 3: Thi thử
        self.option_exam = SourceOption("Thi thử", "Có giới hạn thời gian")
        self.option_group.addButton(self.option_exam.radio, 2)

        for option in (self.option_random, self.option_custom, self.option_exam):
            card_layout.addWidget(option)

        self.option_random.radio.toggled.connect(self._on_option_changed)
        self.option_custom.radio.toggled.connect(self._on_option_changed)
        self.option_exam.radio.toggled.connect(self._on_option_changed)

        layout.addWidget(card)

        # Dynamic content area
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)

        # Content 1: Practice info (for Ngẫu nhiên)
        self.practice_content = self._create_practice_content()
        self.content_stack.addWidget(self.practice_content)

        # Content 2: Custom selection (for Tự chọn)
        self.custom_content = self._create_custom_content()
        self.content_stack.addWidget(self.custom_content)

        # Content 3: Exam settings (for Thi thử)
        self.exam_content = self._create_exam_content()
        self.content_stack.addWidget(self.exam_content)

        # Summary
        self.summary = QLabel()
        self.summary.setObjectName("summaryBox")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        # Start button
        self.start_button = QPushButton("🚀 Bắt đầu tự luyện")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumSize(280, 54)
        self.start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        # Set default
        self.option_random.radio.setChecked(True)
        self._on_option_changed()

        root_layout.addWidget(page)

    def _create_practice_content(self) -> QWidget:
        """Create practice mode content widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        info = QLabel(
            "Tự luyện 10 tình huống theo cấu trúc chuẩn đề thi và phản hồi "
            "đúng/sai ngay sau mỗi tình huống."
        )
        info.setObjectName("noticeBox")
        info.setWordWrap(True)
        layout.addWidget(info)
        return widget

    def _create_custom_content(self) -> QWidget:
        """Create custom selection content widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(12)
        label = QLabel("Danh sách tình huống")
        label.setObjectName("fieldLabel")
        self.custom_button = QPushButton("Mở danh sách 120 tình huống")
        self.custom_button.setObjectName("secondaryActionButton")
        self.custom_button.clicked.connect(self._choose_custom_situations)
        self.custom_count = QLabel("Chưa chọn tình huống")
        self.custom_count.setObjectName("mutedText")
        row.addWidget(label)
        row.addWidget(self.custom_button)
        row.addWidget(self.custom_count)
        row.addStretch()
        layout.addLayout(row)

        hint = QLabel(
            "Có thể tìm kiếm, lọc theo chương và chọn bất kỳ tình huống nào để luyện tập."
        )
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return widget

    def _create_exam_content(self) -> QWidget:
        """Create exam mode content widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        info = QLabel(
            "Thi thử gồm 10 tình huống theo cấu trúc chuẩn đề thi GPLX.\n"
            "Học viên sẽ có 10 phút làm bài. Không hiển thị đáp án trong lúc làm bài."
        )
        info.setObjectName("noticeBox")
        info.setWordWrap(True)
        layout.addWidget(info)

        return widget

    def _on_option_changed(self) -> None:
        """Handle option radio button change."""
        if self.option_random.radio.isChecked():
            self.content_stack.setCurrentIndex(0)
            self.summary.setText("10 tình huống · Cấu trúc chuẩn đề thi")
            self.start_button.setText("Bắt đầu tự luyện")
        elif self.option_custom.radio.isChecked():
            self.content_stack.setCurrentIndex(1)
            self._update_custom_summary()
        else:
            self.content_stack.setCurrentIndex(2)
            self.summary.setText("10 tình huống · Cấu trúc chuẩn đề thi · 10 phút")
            self.start_button.setText("Bắt đầu thi thử")

    def _update_custom_summary(self) -> None:
        """Update summary for custom selection."""
        count = len(self._custom_situation_ids)
        if count == 0:
            self.summary.setText("Chọn các tình huống bạn muốn luyện tập.")
            self.start_button.setText("Mở danh sách chọn tình huống")
            self.start_button.setEnabled(False)
        else:
            self.summary.setText(f"Đã chọn {count} tình huống để luyện tập.")
            self.start_button.setText("Bắt đầu với danh sách đã chọn")
            self.start_button.setEnabled(True)

    def _choose_custom_situations(self) -> None:
        """Open situation selection dialog."""
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
        self._update_custom_summary()

    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        if self.option_random.radio.isChecked():
            self.start_requested.emit("practice", "random", None, 0)
        elif self.option_custom.radio.isChecked():
            if not self._custom_situation_ids:
                QMessageBox.information(
                    self,
                    "Chưa chọn tình huống",
                    "Hãy mở danh sách và chọn ít nhất một tình huống.",
                )
                return
            selection = sorted(self._custom_situation_ids)
            self.start_requested.emit("practice", "custom", selection, 0)
        else:
            duration = 10 * 60  # 10 minutes fixed
            self.start_requested.emit("mock_exam", "exam", None, duration)


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
        heading = QLabel("KIỂM TRA KẾT THÚC MÔN")
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
            "Phần Kiểm tra kết thúc môn đã được dựng giao diện. Danh sách khóa thi và dữ liệu "
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
        self._part_boxes: dict[int, QGroupBox] = {}
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
        self.previous_button = QPushButton("Câu trước")
        self.previous_button.clicked.connect(lambda: self._move_relative(-1))
        self.next_button = QPushButton("Câu tiếp")
        self.next_button.clicked.connect(lambda: self._move_relative(1))
        self.finish_button = QPushButton("Kết thúc sớm")
        self.finish_button.setObjectName("dangerButton")
        self.finish_button.clicked.connect(self._request_finish)
        self.submit_button = QPushButton("Kiểm tra đáp án")
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.clicked.connect(self._submit)
        footer.addWidget(self.progress_label)
        footer.addStretch()
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        footer.addWidget(self.finish_button)
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
        if self._state.mode == "practice":
            title = f"Tự luyện · Tình huống số {situation.id}"
        else:
            mode_name = (
                "Kiểm tra kết thúc môn"
                if self._state.mode == "official_exam"
                else "Thi thử"
            )
            title = f"{mode_name} · Câu số {self._state.current_index + 1}"
        self.position_label.setText(title)
        self._update_progress_label()

        for index, part in enumerate(situation.parts, start=1):
            box = QGroupBox(f"Phần {index}: {part.prompt}")
            box_layout = QVBoxLayout(box)
            group = QButtonGroup(box)
            group.setExclusive(True)
            self._part_boxes[part.id] = box
            self._groups[part.id] = group
            for answer_index, answer in enumerate(part.answers):
                label = chr(ord("A") + answer_index)
                option = AnswerOption(label, answer.text)
                group.addButton(option.radio, answer.id)
                option.radio.toggled.connect(self._answer_selection_changed)
                self._answer_options[answer.id] = option
                box_layout.addWidget(option)
            self.questions_layout.addWidget(box)

        existing_result = self._result_for_situation(situation.id)
        draft = self._draft_selections.get(situation.id, {})
        if self._is_exam_mode() and draft:
            saved_selections = draft
        elif existing_result is not None:
            saved_selections = {
                part.part_id: part.selected_answer_id
                for part in existing_result.parts
                if part.selected_answer_id is not None
            }
        else:
            saved_selections = draft
        for part_id, answer_id in saved_selections.items():
            group = self._groups.get(part_id)
            if group is not None:
                button = group.button(answer_id)
                if button is not None:
                    button.setChecked(True)

        if existing_result is not None and self._state.mode == "practice":
            self._show_feedback(existing_result)
            self._checked = True
        self._load_video(situation)
        self._update_quick_navigation()
        self._update_action_controls()

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
        existing_result = self._result_for_situation(self._state.current.id)
        if existing_result is not None:
            if self._state.mode == "practice":
                self._checked = True
                self._show_feedback(existing_result)
                self._update_action_controls()
                return
            self._advance_or_finish()
            return
        if self._state.mode == "practice" and self._checked:
            return
        if self._is_exam_mode() and self._all_situations_answered():
            self._confirm_complete_exam()
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
        self._update_action_controls()

    def _answer_selection_changed(self) -> None:
        if self._state is None:
            return
        selections = self._selected_answers()
        previous = self._draft_selections.get(self._state.current.id, {})
        newly_selected_part = next(
            (
                part_id
                for part_id in self._groups
                if part_id in selections
                and previous.get(part_id) != selections[part_id]
            ),
            None,
        )
        if selections:
            self._draft_selections[self._state.current.id] = selections
        else:
            self._draft_selections.pop(self._state.current.id, None)
        self._update_action_controls()
        if newly_selected_part is not None:
            QTimer.singleShot(0, lambda: self._scroll_to_next_part(newly_selected_part))

    def _scroll_to_next_part(self, current_part_id: int) -> None:
        if self._state is None:
            return
        part_ids = [part.id for part in self._state.current.parts]
        if current_part_id not in part_ids:
            return
        next_index = part_ids.index(current_part_id) + 1
        if next_index >= len(part_ids):
            return
        next_box = self._part_boxes.get(part_ids[next_index])
        if next_box is None:
            return
        bar = self.scroll.verticalScrollBar()
        target = max(0, next_box.pos().y())
        if target > bar.maximum():
            target = bar.maximum()
        bar.setValue(target)

    def _update_action_controls(self) -> None:
        if self._state is None:
            return
        self.previous_button.setEnabled(self._state.current_index > 0)
        self.next_button.setEnabled(self._state.current_index < len(self._state.situations) - 1)
        all_answered = self._all_situations_answered()
        if self._is_exam_mode():
            self.finish_button.setText("Kết thúc sớm")
            self.finish_button.setVisible(not all_answered)
        else:
            self.finish_button.setVisible(True)
            self.finish_button.setText(
                "Kết thúc bài thi" if all_answered else "Kết thúc sớm"
            )

        if self._is_exam_mode() and all_answered:
            self.submit_button.setText("Hoàn thành bài thi")
            self.submit_button.setEnabled(True)
            return

        existing_result = self._result_for_situation(self._state.current.id)
        draft = self._draft_selections.get(self._state.current.id, {})
        if self._state.mode == "practice":
            if existing_result is not None:
                self.submit_button.setText("Đã kiểm tra đáp án")
                self.submit_button.setEnabled(False)
                return
        if existing_result is not None:
            if draft:
                self.submit_button.setText("Nộp câu trả lời")
                self.submit_button.setEnabled(True)
            else:
                self.submit_button.setText("Câu tiếp theo")
                self.submit_button.setEnabled(True)
            return

        remaining = max(0, len(self._groups) - len(self._selected_answers()))
        if remaining:
            self.submit_button.setText(f"Còn {remaining} đáp án chưa chọn")
            self.submit_button.setEnabled(False)
        else:
            self.submit_button.setText(
                "Nộp câu trả lời"
                if self._state.mode == "mock_exam"
                else "Kiểm tra đáp án"
            )
            self.submit_button.setEnabled(True)

    def _is_exam_mode(self) -> bool:
        return self._state is not None and self._state.mode in {
            "mock_exam",
            "official_exam",
        }

    def _confirm_complete_exam(self) -> None:
        answer = QMessageBox.question(
            self,
            "Xác nhận nộp bài",
            "Tất cả các câu trả lời đã được ghi, bạn có chắc chắn nộp bài không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._finish_session("Đã hoàn thành")

    def _all_situations_answered(self) -> bool:
        if self._state is None:
            return False
        results = {result.situation_id: result for result in self._state.results}
        for situation in self._state.situations:
            result = results.get(situation.id)
            if result is not None:
                if any(part.selected_answer_id is None for part in result.parts):
                    return False
                continue
            selections = self._draft_selections.get(situation.id, {})
            if len(selections) != len(situation.parts):
                return False
        return True

    def _remaining_answer_count(self) -> int:
        if self._state is None:
            return 0
        results = {result.situation_id: result for result in self._state.results}
        remaining = 0
        for situation in self._state.situations:
            result = results.get(situation.id)
            if result is not None:
                remaining += sum(part.selected_answer_id is None for part in result.parts)
            else:
                remaining += len(situation.parts) - len(
                    self._draft_selections.get(situation.id, {})
                )
        return remaining

    def _request_finish(self) -> None:
        if self._state is None:
            return
        self._remember_current_selections()
        remaining = self._remaining_answer_count()
        if remaining:
            message = (
                f"Bạn vẫn còn {remaining} đáp án chưa chọn. Các đáp án còn thiếu sẽ được "
                "tính 0 điểm. Bạn muốn kết thúc sớm?"
            )
            reason = "Kết thúc sớm"
        else:
            message = "Bạn đã trả lời đầy đủ. Bạn muốn kết thúc và nộp bài?"
            reason = "Đã hoàn thành"
        answer = QMessageBox.question(self, "Xác nhận kết thúc", message)
        if answer == QMessageBox.StandardButton.Yes:
            self._finish_session(reason)

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

    def _move_relative(self, offset: int) -> None:
        if self._state is None:
            return
        target_index = self._state.current_index + offset
        if 0 <= target_index < len(self._state.situations):
            self._go_to_situation(target_index)

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
        self._remember_current_selections()
        completed_ids = {result.situation_id for result in self._state.results}
        for situation in self._state.situations:
            selections = self._draft_selections.get(situation.id, {})
            if situation.id not in completed_ids and selections:
                self._state.submit_situation(situation, selections)
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
        answer = QMessageBox.question(
            self,
            "Thoát phiên",
            "Tiến độ phiên học này sẽ không được lưu, bạn chắc chắn muốn thoát?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._timer.stop()
            self.player.stop()
            if self._state is not None:
                self.window().history_repository.discard_session(self._state.session_id)
            self._state = None
            self._draft_selections.clear()
            self.exit_requested.emit()

    def _clear_questions(self) -> None:
        self._groups.clear()
        self._part_boxes.clear()
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
        self.resize(860, 440)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Thời gian", "Chế độ", "Số câu", "Điểm", "Thang 10", "Trạng thái"]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for row_index, row in enumerate(history_repository.recent_sessions()):
            self.table.insertRow(row_index)
            values = [
                self._format_timestamp(row["started_at"]),
                "Tự luyện" if row["mode"] == "practice" else "Thi thử",
                row["total_situations"],
                self._format_score(row["score"]),
                self._format_score(row["score_on_ten"]),
                "Hoàn thành" if row["completed_at"] else "Chưa hoàn thành",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.setCurrentCell(-1, -1)
        layout.addWidget(self.table)

    @staticmethod
    def _format_timestamp(value: object) -> str:
        text = str(value)
        try:
            timestamp = datetime.fromisoformat(text)
        except ValueError:
            return text
        return timestamp.strftime("%d/%m/%Y, %H:%M:%S")

    @staticmethod
    def _format_score(value: object | None) -> str:
        if value is None:
            return "-"
        try:
            return f"{float(value):.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return str(value)


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

        self.stack = AnimatedStackedWidget()
        self.setCentralWidget(self.stack)
        self.home_page = HomePage()
        self.study_setup_page = StudySetupPage(content_repository)
        self.official_exam_page = OfficialExamPage()
        self.session_page = SessionPage(videos_directory)
        self.result_page = ResultPage()

        # Stack order: 0=Home, 1=StudySetup, 2=OfficialExam, 3=Session, 4=Result
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.study_setup_page)
        self.stack.addWidget(self.official_exam_page)
        self.stack.addWidget(self.session_page)
        self.stack.addWidget(self.result_page)

        # HomePage signals
        self.home_page.study_requested.connect(self._on_study_requested)
        self.home_page.official_exam_requested.connect(self._on_official_exam_requested)

        # StudySetupPage signals
        self.study_setup_page.start_requested.connect(self._start_study_session)
        self.study_setup_page.history_requested.connect(self._show_history)
        self.study_setup_page.home_requested.connect(self._on_home_requested)

        # OfficialExamPage signals
        self.official_exam_page.home_requested.connect(self._on_home_requested)

        # SessionPage signals
        self.session_page.finished.connect(self._show_result)
        self.session_page.exit_requested.connect(self._on_home_requested)

        # ResultPage signals
        self.result_page.setup_requested.connect(self._on_study_requested)
        self.result_page.home_requested.connect(self._on_home_requested)

        self._show_home()

    def _on_study_requested(self) -> None:
        self.stack.slide_to_index(1, "left")

    def _on_official_exam_requested(self) -> None:
        self.stack.slide_to_index(2, "left")

    def _on_home_requested(self) -> None:
        self.stack.slide_to_index(0, "right")

    def _start_study_session(
        self,
        mode: str,
        source: str,
        selection: object,
        duration_seconds: int,
    ) -> None:
        try:
            if source == "custom":
                situations = self.content_repository.get_situations_by_ids(
                    [int(identifier) for identifier in selection]
                )
            elif source in ("random", "exam"):
                situations = self.content_repository.get_exam_situations()
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
        self.stack.slide_to_index(3, "left")

    def _show_result(
        self, score: float, correct: int, total: int, mode: str, reason: str
    ) -> None:
        self.result_page.show_result(score, correct, total, mode, reason)
        self.stack.slide_to_index(4, "left")

    def _show_history(self) -> None:
        HistoryDialog(self.history_repository, self).exec()

    def _show_home(self) -> None:
        self.stack.setCurrentIndex(0)
