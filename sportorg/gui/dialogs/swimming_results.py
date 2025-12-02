import logging
from collections import defaultdict
from typing import Any, List, Optional, Union

from PySide6.QtCore import (
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QRegularExpression,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QIntValidator,
    QKeyEvent,
    QKeySequence,
    QRegularExpressionValidator,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemDelegate,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from sportorg.common.otime import OTime
from sportorg.gui.dialogs.person_edit import PersonEditDialog
from sportorg.gui.dialogs.result_edit import ResultEditDialog
from sportorg.gui.global_access import GlobalAccess
from sportorg.language import translate
from sportorg.models.memory import (
    Limit,
    Person,
    Result,
    ResultManual,
    ResultStatus,
    race,
)
from sportorg.models.result.result_tools import recalculate_results
from sportorg.modules.live.live import live_client
from sportorg.modules.teamwork.teamwork import Teamwork

# TODO:
# * [ ] Проверить, проработать фокус ввода
#   * [ ] Что всегда верхняя левая ячейка
#   * [ ] Как действует табуляция?
# * [+] Горячие клавиши:
#   * [+] Alt+Left, Alt+Right — предыдущий, следующий заплыв
#   * [+] Alt+Home, Alt+End — первый, последний заплыв
#   * [+] Enter — следующая ячейка; завершить редактирование и следующая ячейка (как в Excel)
#   * [+] Ctrl+S — применить изменения
#   * [+] DoubleClick по имени — редактировать спортсмена
#   * [+] DoubleClick по результату — редактировать результат?
# * [ ] Перевод
#   * [ ] Input
#   * [ ] Organization = Представитель
#   * [ ] Apply
#   * [ ] Полное наименование = Фамилия, имя
#   * [ ] Текущий заплыв = Текущий
# * [+] Отправка результатов онлайн
#   * [+] В нужном порядке, чтобы первые пять были с лучшим результатом
# * [+] Обработка DNS и DNF
# * [ ] Окно настроек
#   * [ ] Количество дорожек
#   * [ ] Сохранять в настройках SportOrg
# * [ ] Столбец: группа
# * [ ] Столбец: место / финишировало / всего
# * [ ] Стили
#   * [ ] Номер заплыва: крупный, по центру, более узкое поле
#   * [ ] Более компактные кнопки << < > >>
#   * [ ] Более крупный Input
#   * [ ] Адекватные размеры окна
# * [ ] Создание SwimmingResultsModel() в __init__() лишнее? Создаётся в load_heat() сразу после этого

# Supported status inputs (case-insensitive)
DNS_INPUTS = {"dns", "днс", "нстарт", "н/старт"}
DNF_INPUTS = {"dnf", "днф", "н/финиш"}


class PoolTimeConverter:
    @staticmethod
    def otime_to_input(otime: Optional[OTime]) -> int:
        if otime:
            return (
                otime.hour * 1000000
                + otime.minute * 10000
                + otime.sec * 100
                + otime.msec // 10
            )
        return 0

    @staticmethod
    def result_to_input(result: Optional[Result]) -> int:
        if result and result.finish_time:
            return PoolTimeConverter.otime_to_input(result.finish_time)
        return 0

    @staticmethod
    def input_to_otime(input_value: int) -> OTime:
        if input_value:
            hour = input_value // 1000000
            minute = (input_value % 1000000) // 10000
            sec = (input_value % 10000) // 100
            msec = (input_value % 100) * 10
            return OTime(hour=hour, minute=minute, sec=sec, msec=msec)
        return OTime()

    @staticmethod
    def input_to_str(input_value: int) -> str:
        otime = PoolTimeConverter.input_to_otime(input_value)
        time_accuracy = race().get_setting("time_accuracy", 0)
        time_str = otime.to_str(time_accuracy)  # type: ignore
        if time_str.startswith("00:"):
            time_str = time_str[3:]  # strip leading hours if zero
        return time_str


class InputDelegate(QStyledItemDelegate):
    """Delegate for Input column: accepts integers, mm:ss.hh format, or status strings like DNS/DNF."""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Accept integer digits, mm:ss.hh or status words (latin/cyrillic, slashes)
        regex = QRegularExpression(r"^[0-9]+$|^[A-Za-zА-Яа-я/\\]+$")
        validator = QRegularExpressionValidator(regex, editor)
        editor.setValidator(validator)
        editor.installEventFilter(self)
        return editor

    def setEditorData(self, editor, index):
        if not isinstance(editor, QLineEdit):
            return
        try:
            value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                editor.setText(str(value))
                editor.selectAll()
        except Exception:
            pass

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if (
            isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            widget = object
            while widget is not None:
                widget = widget.parent()
                if isinstance(widget, QTableView):
                    break
            view = widget
            if isinstance(object, QLineEdit) and isinstance(view, QTableView):
                view.commitData(object)
                view.closeEditor(object, QAbstractItemDelegate.EndEditHint.NoHint)

            return False
        return super().eventFilter(object, event)


class BibDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QIntValidator(0, Limit.BIB, editor)
        editor.setValidator(validator)
        # editor.installEventFilter(self)
        return editor

    def setEditorData(self, editor, index):
        if not isinstance(editor, QLineEdit):
            return
        try:
            value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                editor.setText(str(value))
                editor.selectAll()
        except Exception:
            pass

    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if (
            isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            widget = object
            while widget is not None:
                widget = widget.parent()
                if isinstance(widget, QTableView):
                    break
            view = widget
            if isinstance(object, QLineEdit) and isinstance(view, QTableView):
                view.commitData(object)
                view.closeEditor(object, QAbstractItemDelegate.EndEditHint.NoHint)

            return False
        return super().eventFilter(object, event)


def parse_pool_time_str(s: str) -> OTime:
    """Parse string like 'mm:ss.hh' into OTime.

    Empty or whitespace string -> OTime() (zero time).
    Raises ValueError on invalid format.
    """
    if s is None:
        return OTime()
    s = str(s).strip()
    if s == "":
        return OTime()

    # Expect mm:ss.hh where mm may be one or more digits
    try:
        if ":" not in s:
            raise ValueError("Invalid time format")
        minute_part, sec_part = s.split(":", 1)
        if "." in sec_part:
            sec_str, hund_str = sec_part.split(".", 1)
        else:
            sec_str = sec_part
            hund_str = "0"

        minutes = int(minute_part)
        seconds = int(sec_str)
        hundreds = int(hund_str.ljust(2, "0")[:2])  # pad/truncate to 2 digits

        if seconds < 0 or seconds >= 60 or hundreds < 0 or hundreds >= 100:
            raise ValueError("Invalid time values")

        hours = minutes // 60
        minutes = minutes % 60
        return OTime(hour=hours, minute=minutes, sec=seconds, msec=hundreds * 10)
    except Exception as e:
        raise ValueError(f"Cannot parse time '{s}': {e}")


class SwimmingResultsModel(QAbstractTableModel):
    """Table model with rows = Person, columns = Result, Bib, Full name, Organization."""

    COL_INPUT = 0
    COL_RESULT = 1
    COL_BIB = 2
    COL_FULLNAME = 3
    COL_ORG = 4

    POOL_SIZE = 6

    HEADERS = [
        translate("Input"),
        translate("Result"),
        translate("Bib"),
        translate("Full name"),
        translate("Organization"),
    ]

    DNS_INPUTS = DNS_INPUTS
    DNF_INPUTS = DNF_INPUTS

    def __init__(
        self, persons: List[Person], results_map: dict, parent: Optional[Any] = None
    ):
        super().__init__(parent)
        WRONG_LANE = -1
        lane_persons = defaultdict(list)
        for person in persons:
            if person.bib is None:
                lane_persons[0].append(person)
            else:
                lane = ((person.bib - 1) % 10) + 1
                if lane <= 0 or lane > self.POOL_SIZE:
                    lane = WRONG_LANE
                lane_persons[lane].append(person)

        # Compute max_slots for main lanes
        max_slots = 0
        for lane in range(1, self.POOL_SIZE + 1):
            max_slots = max(max_slots, len(lane_persons[lane]))

        self._rows = []

        # Padded main lanes
        for lane in range(1, self.POOL_SIZE + 1):
            lane_list = sorted(lane_persons[lane], key=lambda p: p.bib or 0)
            for person in lane_list:
                result = results_map.get(person.id)
                self._rows.append(self._make_lane_record(person, result, lane))

            # Pad empty slots
            for _ in range(len(lane_list), max_slots):
                self._rows.append(self._make_lane_record(None, None, lane))

        # Lane -1 at end
        lane = WRONG_LANE
        for person in lane_persons[lane]:
            result = results_map.get(person.id)
            self._rows.append(self._make_lane_record(person, result, lane))

    def _make_lane_record(
        self, person: Optional[Person], result: Optional[Result], lane: int = 0
    ):
        if not person:
            person = Person()
        # Default input is numeric code for OTime when result is OK
        if result and not result.is_status_ok():
            input_int = 0
            input_status = result.status_comment or (
                result.status.get_title() if result.status else ""
            )
        else:
            input_int = PoolTimeConverter.result_to_input(result)
            input_status = None
        record = {
            "person": person,
            "result": result,
            "input_int": input_int,
            "input_status": input_status,
            "modified": False,
            "lane": lane,
            "bib": person.bib,
        }
        return record

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return len(self._rows)

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex()
    ) -> int:
        return 5

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        elif orientation == Qt.Orientation.Vertical:
            # Lane numbering
            row = section
            if 0 <= row < len(self._rows):
                lane = self._rows[row]["lane"]
                return str(lane) if lane is not None else ""
        return None

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role=Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        item = self._rows[row]
        person: Person = item["person"] or Person()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_INPUT:
                # If user or initial result marked a status (DNS/DNF), display it in Input column
                status_text = item.get("input_status")
                if status_text:
                    return status_text
                return str(item.get("input_int", 0)) if item.get("input_int", 0) else ""
            elif col == self.COL_RESULT:
                # If there is an in-progress input status, show it as preview
                status_text = item.get("input_status")
                if status_text:
                    return status_text
                # If stored result is present but shows non-ok, display its status_comment
                result = item.get("result")
                if result and not result.is_status_ok():
                    return result.status_comment or (
                        result.status.get_title() if result.status else ""
                    )
                input_int = item.get("input_int", 0)
                return PoolTimeConverter.input_to_str(input_int)
            elif col == self.COL_BIB:
                return str(person.bib)
            elif col == self.COL_FULLNAME:
                return person.full_name
            elif col == self.COL_ORG:
                return person.organization.name if person.organization else ""
        # Align numeric columns to the right
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_INPUT, self.COL_RESULT, self.COL_BIB):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return None

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if index.column() in (self.COL_INPUT, self.COL_BIB):
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        value,
        role=Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        row = index.row()
        col = index.column()
        item = self._rows[row]
        try:
            if col == self.COL_INPUT:
                str_value = str(value).strip() if value is not None else ""
                if str_value == "":
                    input_int = 0
                    item["input_status"] = None
                else:
                    # Check for status inputs (dns/dnf variants)
                    status_parsed = self.parse_status_input(str_value)
                    if status_parsed:
                        # status_parsed = (ResultStatus, comment, finish_otime)
                        item["input_int"] = 0
                        item["input_status"] = status_parsed[1]
                        item["modified"] = True
                        # update result cell preview
                        idx_result = self.index(row, self.COL_RESULT)
                        self.dataChanged.emit(
                            index, index, [Qt.ItemDataRole.DisplayRole]
                        )
                        self.dataChanged.emit(
                            idx_result, idx_result, [Qt.ItemDataRole.DisplayRole]
                        )
                        return True
                    # Try mm:ss.hh format
                    if ":" in str_value:
                        try:
                            otime = parse_pool_time_str(str_value)
                            input_int = PoolTimeConverter.otime_to_input(otime)
                        except ValueError as ve:
                            raise ValueError(str(ve))
                    else:
                        # fallback to numeric digits
                        input_int = int(str_value)
                        if input_int < 0:
                            raise ValueError("Input must be non-negative integer")
                    # numeric time -> clear status
                    item["input_status"] = None
                item["input_int"] = input_int
                item["modified"] = True
                # Also update result cell
                idx_result = self.index(row, self.COL_RESULT)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                self.dataChanged.emit(
                    idx_result, idx_result, [Qt.ItemDataRole.DisplayRole]
                )
                return True
            elif col == self.COL_BIB:
                str_value = str(value).strip() if value is not None else ""
                if str_value == "":
                    bib = 0
                else:
                    bib = int(str_value)
                    if bib < 0 or bib > Limit.BIB:
                        raise ValueError(f"Bib must be between 0 and {Limit.BIB}")
                item["bib"] = bib
                item["person"].set_bib(bib)
                if item["result"]:
                    item["result"].bib = bib
                item["modified"] = True
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                return True
            else:
                return False
        except ValueError as e:
            parent = QApplication.activeWindow()
            QMessageBox.warning(parent, translate("Invalid input"), str(e))
            return False

    def get_row(self, row: int):
        return self._rows[row]

    def apply_to_race(self, race_obj):
        """Apply modified rows into given race() object (in-memory)."""
        has_changes = False
        changed_results = []
        for item in reversed(self._rows):
            if not item.get("modified", False):
                continue
            person: Person = item["person"]
            input_int = item.get("input_int", 0)
            # get OTime and status
            status_preview = item.get("input_status")
            if status_preview:
                # map preview to actual status (DNS/DNF)
                parsed = self.parse_status_input(status_preview)
                if parsed:
                    _, comment, finish_otime = parsed
                    otime = finish_otime
                else:
                    otime = OTime()
            else:
                if input_int:
                    otime = PoolTimeConverter.input_to_otime(input_int)
                else:
                    otime = OTime()

            # find existing result
            result = race_obj.find_person_result(person)
            if result:
                result.finish_time = otime
                # set the status/comment based on input
                if status_preview:
                    parsed = self.parse_status_input(status_preview)
                    if parsed:
                        status_enum, comment, _ = parsed
                        result.status = status_enum
                        result.status_comment = comment
                else:
                    # Numeric time -> mark as OK
                    result.status = ResultStatus.OK
                    result.status_comment = ""
                result.person = person
                result.bib = person.bib
                has_changes = True
            else:
                # create new manual result if input not zero OR create even for zero as requested
                result = race_obj.new_result(ResultManual)
                result.person = person
                result.finish_time = otime
                if status_preview:
                    parsed = self.parse_status_input(status_preview)
                    if parsed:
                        status_enum, comment, _ = parsed
                        result.status = status_enum
                        result.status_comment = comment
                else:
                    result.status = ResultStatus.OK
                    result.status_comment = ""
                result.bib = person.bib
                race_obj.add_new_result(result)
                has_changes = True

            changed_results.append(result)
            item["modified"] = False

        if has_changes:
            race_obj.update_counters()
            recalculate_results(recheck_results=False)
            data = sorted(changed_results, key=lambda r: r.get_result(), reverse=True)
            live_client.send(data)
            Teamwork().send([r.to_dict() for r in changed_results])
            app_obj = GlobalAccess().get_app()
            if app_obj is not None:
                main_window = app_obj.get_main_window()
                if main_window is not None:
                    main_window.refresh()

    def parse_status_input(self, input: str):
        """Parse a status string input and return a tuple (status_enum, comment, finish_otime) or None.

        Accepts many variants, returns the canonical ResultStatus and string comment (DNS/DNF)
        and finish time 23:59:59.00.
        """
        if not input:
            return None
        input = str(input).strip().lower()
        if input in self.DNS_INPUTS:
            # DID_NOT_START
            finish = OTime(hour=23, minute=59, sec=59, msec=0)
            return (ResultStatus.DID_NOT_START, "DNS", finish)
        if input in self.DNF_INPUTS:
            # DID_NOT_FINISH
            finish = OTime(hour=23, minute=59, sec=59, msec=0)
            return (ResultStatus.DID_NOT_FINISH, "DNF", finish)
        return None


class SwimmingResultsDialog(QDialog):
    # nav state placeholders
    heat_first: Optional[int] = None
    heat_prev: Optional[int] = None
    heat_next: Optional[int] = None
    heat_last: Optional[int] = None
    heat_current: Optional[int] = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Swimming Results"))
        self.setModal(True)
        self.race_obj = race()

        self._init_layout()

        self._init_connections()

        self.load_initial_heat()

    def _init_layout(self):
        self._init_header()
        self._init_model_view()
        self._init_bottom_buttons()

        self.layout_ = QVBoxLayout(self)
        self.layout_.addWidget(self.header)
        self.layout_.addWidget(self.view)
        self.layout_.addWidget(self.button_box)

    def _init_header(self):
        self.header = QWidget(self)
        header_layout = QHBoxLayout(self.header)

        self.button_current = QPushButton(translate("Текущий заплыв"), self)
        header_layout.addWidget(self.button_current)

        # center group
        center = QWidget(self)
        center_layout = QHBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        self.button_first = QPushButton(self)
        self.button_prev = QPushButton(self)
        self.heat_input = QLineEdit(self)
        self.heat_input.setValidator(QIntValidator(0, 999, self.heat_input))
        self.heat_input.setFixedWidth(36)
        self.button_next = QPushButton(self)
        self.button_last = QPushButton(self)
        for b in (
            self.button_first,
            self.button_prev,
            self.button_next,
            self.button_last,
        ):
            b.setFixedWidth(48)
        center_layout.addWidget(self.button_first)
        center_layout.addWidget(self.button_prev)
        center_layout.addWidget(self.heat_input)
        center_layout.addWidget(self.button_next)
        center_layout.addWidget(self.button_last)

        header_layout.addStretch()
        header_layout.addWidget(center)
        header_layout.addStretch()

    def _init_bottom_buttons(self):
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )
        self.button_ok = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.button_apply = button_box.button(QDialogButtonBox.StandardButton.Apply)
        self.button_cancel = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.button_reset = button_box.button(QDialogButtonBox.StandardButton.Reset)

        self.button_ok.setText(translate("OK"))
        self.button_apply.setText(translate("Apply"))
        self.button_cancel.setText(translate("Cancel"))
        self.button_reset.setText(translate("Сбросить"))

        self.button_box = button_box

    def _init_model_view(self):
        self.model = SwimmingResultsModel([], {}, parent=self)

        self.view = QTableView(self)
        self.view.sizeHint = lambda: QSize(600, 500)

        self.view.setItemDelegateForColumn(
            self.model.COL_INPUT, InputDelegate(self.view)
        )
        self.view.setItemDelegateForColumn(self.model.COL_BIB, BibDelegate(self.view))

    def _init_connections(self):
        # wire navigation signals
        self.button_first.clicked.connect(lambda: self.try_change_heat(self.heat_first))
        self.button_prev.clicked.connect(lambda: self.try_change_heat(self.heat_prev))
        self.button_next.clicked.connect(lambda: self.try_change_heat(self.heat_next))
        self.button_last.clicked.connect(lambda: self.try_change_heat(self.heat_last))
        self.button_current.clicked.connect(self.on_current_heat_requested)
        self.heat_input.editingFinished.connect(self.on_heat_input_finished)

        # wire bottom buttons
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)
        self.button_apply.clicked.connect(self.on_apply)
        self.button_reset.clicked.connect(self.on_reset)

        # Shortcuts
        self.button_prev.setToolTip("Alt+Left")
        self.button_next.setToolTip("Alt+Right")
        self.button_first.setToolTip("Alt+Home")
        self.button_last.setToolTip("Alt+End")
        self.button_apply.setToolTip("Ctrl+S")

        shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        shortcut.activated.connect(lambda: self.try_change_heat(self.heat_prev))
        shortcut = QShortcut(QKeySequence("Alt+Right"), self)
        shortcut.activated.connect(lambda: self.try_change_heat(self.heat_next))
        shortcut = QShortcut(QKeySequence("Alt+Home"), self)
        shortcut.activated.connect(lambda: self.try_change_heat(self.heat_first))
        shortcut = QShortcut(QKeySequence("Alt+End"), self)
        shortcut.activated.connect(lambda: self.try_change_heat(self.heat_last))
        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(self.on_apply)

        self.view.doubleClicked.connect(self._on_double_click)
        self.installEventFilter(self)

    def eventFilter(self, arg__1: QObject, arg__2: QEvent) -> bool:
        obj, event = arg__1, arg__2
        if isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            if event.key() in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ) and event.modifiers() in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.KeypadModifier,
            ):
                col = self.view.currentIndex().column()
                row = self.view.currentIndex().row()
                if row < self.model.rowCount() - 1:
                    self.view.setCurrentIndex(self.model.index(row + 1, col))
                return True
            elif event.key() == Qt.Key.Key_Escape:
                self.on_cancel()
                return True

        return super().eventFilter(obj, event)

    def on_apply(self):
        try:
            self.model.apply_to_race(self.race_obj)
        except Exception:
            logging.exception("Error applying swimming results")
        self._update_bottom_buttons()

    def on_ok(self):
        if self.has_unsaved_changes():
            parent = QApplication.activeWindow()
            msg = QMessageBox(parent)
            msg.setWindowTitle(translate("Unsaved changes"))
            msg.setText(translate("Do you want to save changes before closing?"))
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            res = msg.exec()
            if res == QMessageBox.StandardButton.Yes:
                self.on_apply()
                self.accept()
            elif res == QMessageBox.StandardButton.No:
                self.accept()

    def on_cancel(self):
        if self.has_unsaved_changes():
            parent = QApplication.activeWindow()
            msg = QMessageBox(parent)
            msg.setWindowTitle(translate("Unsaved changes"))
            msg.setText(translate("You need to apply changes before closing"))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        else:
            self.reject()

    def on_reset(self):
        # reload current heat from race_obj
        self.load_heat(self.heat_current)

    def closeEvent(self, arg__1):
        if self.has_unsaved_changes():
            self.on_cancel()
            event = arg__1
            event.ignore()

    def _on_double_click(self, index: Union[QModelIndex, QPersistentModelIndex]):
        # Called when user double-clicks a cell in the view.
        if not index or not index.isValid():
            return
        row = index.row()
        col = index.column()
        item = self.model.get_row(row)
        # Double-click on full name or organization -> edit person
        if col in (self.model.COL_FULLNAME, self.model.COL_ORG):
            person = item.get("person")
            if person:
                PersonEditDialog(person).exec_()
                self.load_heat(self.heat_current)
        # Double-click on result -> edit result if present
        elif col == self.model.COL_RESULT:
            result = item.get("result")
            if result:
                ResultEditDialog(result).exec_()
                self.load_heat(self.heat_current)

    def _update_bottom_buttons(self):
        has_unsaved_changes = self.has_unsaved_changes()
        self.button_apply.setEnabled(has_unsaved_changes)
        self.button_reset.setEnabled(has_unsaved_changes)

    def _update_nav_buttons(self):
        heats = self.get_available_heats()
        if not heats:
            self.heat_first = None
            self.heat_prev = None
            self.heat_next = None
            self.heat_last = None
        else:
            if self.heat_current is None:
                idx = 0
            else:
                try:
                    idx = heats.index(self.heat_current)
                except ValueError:
                    idx = 0
            self.heat_first = heats[0] if idx > 0 else None
            self.heat_prev = heats[idx - 1] if idx > 0 else None

            self.heat_last = heats[-1] if idx < len(heats) - 1 else None
            self.heat_next = heats[idx + 1] if idx < len(heats) - 1 else None

        self._set_btn_text(self.button_first, "<<", self.heat_first)
        self._set_btn_text(self.button_prev, "<", self.heat_prev)
        self._set_btn_text(self.button_next, ">", self.heat_next)
        self._set_btn_text(self.button_last, ">>", self.heat_last)

        if self.heat_current is None:
            self.heat_input.setText("")
        else:
            self.heat_input.setText(str(self.heat_current))

    def _set_btn_text(self, btn, prefix, heat):
        if heat is None:
            btn.setText("")
            btn.setEnabled(False)
        else:
            btn.setText(f"{prefix} {heat}")
            btn.setEnabled(True)

    def load_initial_heat(self):
        heats = self.get_available_heats()
        if not heats:
            self.heat_current = None
            self._update_nav_buttons()
            return
        first_unfinished = self.find_first_unfinished_heat()
        chosen = first_unfinished if first_unfinished is not None else heats[0]
        self.try_change_heat(chosen, force=True)

    def get_available_heats(self) -> List[int]:
        return sorted({p.start_group for p in self.race_obj.persons})

    def find_first_unfinished_heat(self) -> Optional[int]:
        heats = self.get_available_heats()
        for h in heats:
            persons = [p for p in self.race_obj.persons if p.start_group == h]
            if not any([self.race_obj.find_person_result(p) for p in persons]):
                return h
        return None

    def on_heat_input_finished(self):
        txt = self.heat_input.text().strip()
        if txt == "":
            return
        try:
            new_heat = int(txt)
        except Exception:
            return
        self.try_change_heat(new_heat)

    def on_current_heat_requested(self):
        h = self.find_first_unfinished_heat()
        if h is None:
            heats = self.get_available_heats()
            h = heats[0] if heats else None
        if h is not None:
            self.try_change_heat(h)

    def try_change_heat(self, new_heat: Optional[int], force: bool = False):
        if new_heat == self.heat_current and not force:
            return
        if not force and self.has_unsaved_changes():
            parent = QApplication.activeWindow()
            msg = QMessageBox(parent)
            msg.setWindowTitle(translate("Unsaved changes"))
            msg.setText(translate("There are unsaved changes in the current heat."))
            msg.setStandardButtons(
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel
            )
            res = msg.exec()
            if res == QMessageBox.StandardButton.Save:
                try:
                    self.on_apply()
                except Exception:
                    logging.exception("Error applying changes before heat change")
                    return
            else:
                if self.heat_current is not None:
                    self.heat_input.setText(str(self.heat_current))
                return
        self.load_heat(new_heat)

    def load_heat(self, start_group: Optional[int]):
        if start_group is None:
            persons = []
            results_map = {}
        else:
            persons = sorted(
                [p for p in self.race_obj.persons if p.start_group == start_group],
                key=lambda p: p.bib,
            )
            results_map = {
                r.person.id: r
                for r in self.race_obj.results
                if r.person and r.person.start_group == start_group
            }

        self.model = SwimmingResultsModel(persons, results_map, parent=self)
        self.model.dataChanged.connect(self._update_bottom_buttons)
        self.view.setModel(self.model)
        self.view.resizeColumnsToContents()

        self.heat_current = start_group
        if not persons:
            self.heat_input.setStyleSheet("background: #fff0f0")
        else:
            self.heat_input.setStyleSheet("")

        self._update_nav_buttons()
        self._update_bottom_buttons()

    def has_unsaved_changes(self) -> bool:
        try:
            for row in getattr(self.model, "_rows", []):
                if row.get("modified", False):
                    return True
        except Exception:
            pass
        return False
