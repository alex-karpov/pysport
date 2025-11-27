import logging
from typing import Any, List, Optional, Union

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QRegularExpression,
    QSize,
    Qt,
)
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
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
from sportorg.language import translate
from sportorg.models.memory import Person, ResultManual, race


class PoolTimeConverter:
    @staticmethod
    def otime_to_input(otime: OTime) -> int:
        if otime:
            return (
                otime.hour * 1000000
                + otime.minute * 10000
                + otime.sec * 100
                + otime.msec // 10
            )
        return 0

    @staticmethod
    def inout_to_otime(input_value: int) -> OTime:
        if input_value:
            hour = input_value // 1000000
            minute = (input_value % 1000000) // 10000
            sec = (input_value % 10000) // 100
            msec = (input_value % 100) * 10
            return OTime(hour=hour, minute=minute, sec=sec, msec=msec)
        return OTime()

    @staticmethod
    def input_to_str(input_value: int) -> str:
        if input_value:
            otime = PoolTimeConverter.inout_to_otime(input_value)
            minute = otime.hour * 60 + otime.minute
            sec = otime.sec
            hundreds = otime.msec // 10
            return f"{minute:02}:{sec:02}.{hundreds:02}"
        return "00:00.00"


class InputIntDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QIntValidator(0, 9999999, editor)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        # Populate editor with current display value and select all text
        if not isinstance(editor, QLineEdit):
            return
        try:
            value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                editor.setText(str(value))
                editor.selectAll()
        except Exception:
            # Be defensive: don't break editing if something unexpected happens
            pass


class PoolTimeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Accept mm:ss.hh or m:ss.hh, up to 3 digits for minutes, 2 for seconds, 2 for hundreds
        regex = QRegularExpression(r"^\d{1,3}:[0-5]\d(\.\d{1,2})?$")
        validator = QRegularExpressionValidator(regex, editor)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        # Populate editor with current display value and select all text
        if not isinstance(editor, QLineEdit):
            return
        try:
            value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                editor.setText(str(value))
                editor.selectAll()
        except Exception:
            pass


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

    HEADERS = ["Input", "Result", "Bib", "Full name", "Organization"]

    def __init__(
        self, persons: List[Person], results_map: dict, parent: Optional[Any] = None
    ):
        super().__init__(parent)
        # rows: list of dict {person, result, input_int, modified}
        self._rows = []
        for p in persons:
            res = results_map.get(p.id)
            if res and getattr(res, "finish_time", None):
                input_int = PoolTimeConverter.otime_to_input(res.finish_time)
            else:
                input_int = 0
            self._rows.append(
                {
                    "person": p,
                    "result": res,
                    "input_int": input_int,
                    "modified": False,
                }
            )

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
            labels = [
                translate("Input"),
                translate("Result"),
                translate("Bib"),
                translate("Full name"),
                translate("Organization"),
            ]
            return labels[section]
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
        person: Person = item["person"]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_INPUT:
                return str(item.get("input_int", 0)) if item.get("input_int", 0) else ""
            elif col == self.COL_RESULT:
                input_int = item.get("input_int", 0)
                if not input_int:
                    return ""
                otime = PoolTimeConverter.inout_to_otime(input_int)
                minutes = otime.hour * 60 + otime.minute
                seconds = otime.sec
                hundreds = otime.msec // 10
                return f"{minutes:02}:{seconds:02}.{hundreds:02}"
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
        if index.column() in (self.COL_INPUT, self.COL_RESULT):
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
                else:
                    input_int = int(str_value)
                    if input_int < 0:
                        raise ValueError("Input must be non-negative integer")
                item["input_int"] = input_int
                item["modified"] = True
                # Also update result cell
                idx_result = self.index(row, self.COL_RESULT)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                self.dataChanged.emit(
                    idx_result, idx_result, [Qt.ItemDataRole.DisplayRole]
                )
                return True
            elif col == self.COL_RESULT:
                str_value = str(value).strip() if value is not None else ""
                if str_value == "":
                    otime = OTime()
                    input_int = 0
                else:
                    otime = parse_pool_time_str(str_value)
                    input_int = PoolTimeConverter.otime_to_input(otime)
                item["input_int"] = input_int
                item["modified"] = True
                # Also update input cell
                idx_input = self.index(row, self.COL_INPUT)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                self.dataChanged.emit(
                    idx_input, idx_input, [Qt.ItemDataRole.DisplayRole]
                )
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
        changed = False
        for item in self._rows:
            if not item.get("modified", False):
                continue
            person: Person = item["person"]
            input_int = item.get("input_int", 0)
            # get OTime
            if input_int:
                otime = PoolTimeConverter.inout_to_otime(input_int)
            else:
                otime = OTime()

            # find existing result
            existing = race_obj.find_person_result(person)
            if existing:
                existing.finish_time = otime
                existing.person = person
                existing.bib = person.bib
                changed = True
            else:
                # create new manual result if input not zero OR create even for zero as requested
                new_res = race_obj.new_result(ResultManual)
                new_res.person = person
                new_res.finish_time = otime
                new_res.bib = person.bib
                race_obj.add_new_result(new_res)
                changed = True

            # mark as applied
            item["modified"] = False

        if changed:
            try:
                race_obj.update_counters()
            except Exception:
                logging.exception(
                    "Failed to update counters after applying swimming results"
                )


class SwimmingResultsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Swimming Results"))
        self.setModal(True)

        self.race_obj = race()
        self.current_heat: Optional[int] = None

        # Navigation header (Текущий заплыв on left; controls centered)
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
        self.heat_input.setFixedWidth(80)
        self.button_next = QPushButton(self)
        self.button_last = QPushButton(self)
        for b in (
            self.button_first,
            self.button_prev,
            self.button_next,
            self.button_last,
        ):
            b.setFixedWidth(64)
        center_layout.addWidget(self.button_first)
        center_layout.addWidget(self.button_prev)
        center_layout.addWidget(self.heat_input)
        center_layout.addWidget(self.button_next)
        center_layout.addWidget(self.button_last)

        header_layout.addStretch()
        header_layout.addWidget(center)
        header_layout.addStretch()

        # initial full-model load; model will be replaced by load_heat
        persons = sorted(self.race_obj.persons, key=lambda p: p.bib)
        results_map = {r.person.id: r for r in self.race_obj.results if r.person}

        self.model = SwimmingResultsModel(persons, results_map, parent=self)

        self.view = QTableView(self)
        self.view.sizeHint = lambda: QSize(600, 500)
        self.view.setModel(self.model)
        # Set delegates for input/result columns
        self.view.setItemDelegateForColumn(
            self.model.COL_INPUT, InputIntDelegate(self.view)
        )
        self.view.setItemDelegateForColumn(
            self.model.COL_RESULT, PoolTimeDelegate(self.view)
        )
        self.view.resizeColumnsToContents()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_ok = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.button_ok.setText(translate("OK"))
        self.button_apply = button_box.button(QDialogButtonBox.StandardButton.Apply)
        self.button_apply.setText(translate("Apply"))
        self.button_cancel = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.button_cancel.setText(translate("Cancel"))

        button_box.accepted.connect(self.on_ok)
        self.button_apply.clicked.connect(self.on_apply)
        button_box.rejected.connect(self.on_cancel)

        # Reset button in the bottom area
        self.button_reset = QPushButton(translate("Сбросить"), self)
        button_box.addButton(self.button_reset, QDialogButtonBox.ButtonRole.ActionRole)
        self.button_reset.clicked.connect(self.on_reset)

        layout = QVBoxLayout(self)
        layout.addWidget(self.header)
        layout.addWidget(self.view)
        layout.addWidget(button_box)

        # wire navigation signals
        self.button_first.clicked.connect(
            lambda: self.try_change_heat(self._first_heat)
        )
        self.button_prev.clicked.connect(lambda: self.try_change_heat(self._prev_heat))
        self.button_next.clicked.connect(lambda: self.try_change_heat(self._next_heat))
        self.button_last.clicked.connect(lambda: self.try_change_heat(self._last_heat))
        self.button_current.clicked.connect(self.on_current_heat_requested)
        self.heat_input.editingFinished.connect(self.on_heat_input_finished)

        # connect model changes
        try:
            self.model.dataChanged.connect(self._on_model_changed)
        except Exception:
            pass

        # nav state placeholders
        self._first_heat = None
        self._prev_heat = None
        self._next_heat = None
        self._last_heat = None

        # pick initial heat: first unfinished, otherwise first available
        self.load_initial_heat()

    def on_apply(self):
        try:
            self.model.apply_to_race(self.race_obj)
        except Exception:
            logging.exception("Error applying swimming results")

    def on_ok(self):
        if self.has_unsaved_changes():
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
                    logging.exception("Error applying swimming results")
                    return
            else:
                return
        self.accept()

    def on_cancel(self):
        if self.has_unsaved_changes():
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
                    logging.exception("Error applying swimming results")
                    return
            else:
                return
        self.reject()

    def load_initial_heat(self):
        heats = self.get_available_heats()
        if not heats:
            self.current_heat = None
            self.update_nav_buttons()
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
            if not persons:
                continue
            any_with_result = False
            for p in persons:
                res = self.race_obj.find_person_result(p)
                if res and getattr(res, "finish_time", None):
                    any_with_result = True
                    break
            if not any_with_result:
                return h
        return None

    def update_nav_buttons(self):
        heats = self.get_available_heats()
        if not heats:
            self._first_heat = self._prev_heat = self._next_heat = self._last_heat = (
                None
            )
        else:
            self._first_heat = heats[0]
            self._last_heat = heats[-1]
            if self.current_heat is None:
                idx = 0
            else:
                try:
                    idx = heats.index(self.current_heat)
                except ValueError:
                    idx = 0
            self._prev_heat = heats[idx - 1] if idx > 0 else None
            self._next_heat = heats[idx + 1] if idx < len(heats) - 1 else None

        def set_btn_text(btn, prefix, heat):
            if heat is None:
                btn.setText("")
                btn.setEnabled(False)
            else:
                btn.setText(f"{prefix} {heat}")
                btn.setEnabled(True)

        set_btn_text(self.button_first, "<<", self._first_heat)
        set_btn_text(self.button_prev, "<", self._prev_heat)
        set_btn_text(self.button_next, ">", self._next_heat)
        set_btn_text(self.button_last, ">>", self._last_heat)

        if self.current_heat is None:
            self.heat_input.setText("")
        else:
            self.heat_input.setText(str(self.current_heat))

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
        if new_heat == self.current_heat and not force:
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
                if self.current_heat is not None:
                    self.heat_input.setText(str(self.current_heat))
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
        self.view.setModel(self.model)
        self.view.setItemDelegateForColumn(
            self.model.COL_INPUT, InputIntDelegate(self.view)
        )
        self.view.setItemDelegateForColumn(
            self.model.COL_RESULT, PoolTimeDelegate(self.view)
        )
        self.view.resizeColumnsToContents()
        try:
            self.model.dataChanged.connect(self._on_model_changed)
        except Exception:
            pass

        self.current_heat = start_group
        if not persons:
            self.heat_input.setStyleSheet("background: #fff0f0")
        else:
            self.heat_input.setStyleSheet("")

        self.update_nav_buttons()
        self._on_model_changed()

    def has_unsaved_changes(self) -> bool:
        try:
            for row in getattr(self.model, "_rows", []):
                if row.get("modified", False):
                    return True
        except Exception:
            pass
        return False

    def _on_model_changed(self, *args, **kwargs):
        has = self.has_unsaved_changes()
        try:
            self.button_apply.setEnabled(has)
        except Exception:
            pass
        try:
            self.button_reset.setEnabled(has)
        except Exception:
            pass

    def on_reset(self):
        # reload current heat from race_obj
        self.load_heat(self.current_heat)

    def closeEvent(self, arg__1):
        event = arg__1
        if self.has_unsaved_changes():
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
                    logging.exception("Error applying changes on close")
                    event.ignore()
                    return
            else:
                event.ignore()
                return
        event.accept()
