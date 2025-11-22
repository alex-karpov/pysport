import logging
from typing import Any, List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRegularExpression, Qt
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QStyledItemDelegate,
    QTableView,
    QVBoxLayout,
)


class InputIntDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QIntValidator(0, 9999999, editor)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        # Populate editor with current display value and select all text
        try:
            value = index.model().data(index, Qt.DisplayRole)
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
        try:
            value = index.model().data(index, Qt.DisplayRole)
            if value is not None:
                editor.setText(str(value))
                editor.selectAll()
        except Exception:
            pass


from sportorg.common.otime import OTime
from sportorg.gui.dialogs.swimming_results_old import PoolTimeConverter
from sportorg.language import translate
from sportorg.models.memory import Person, ResultManual, race


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

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 5

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            labels = [
                translate("Input"),
                translate("Result"),
                translate("Bib"),
                translate("Full name"),
                translate("Organization"),
            ]
            return labels[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        item = self._rows[row]
        person: Person = item["person"]

        if role == Qt.DisplayRole:
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

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() in (self.COL_INPUT, self.COL_RESULT):
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
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
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                self.dataChanged.emit(idx_result, idx_result, [Qt.DisplayRole])
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
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                self.dataChanged.emit(idx_input, idx_input, [Qt.DisplayRole])
                return True
            else:
                return False
        except ValueError as e:
            QMessageBox.warning(None, translate("Invalid input"), str(e))
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
        # prepare data
        persons = sorted(self.race_obj.persons, key=lambda p: p.bib)
        results_map = {r.person.id: r for r in self.race_obj.results if r.person}

        self.model = SwimmingResultsModel(persons, results_map, parent=self)

        self.view = QTableView(self)
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
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        self.button_ok = button_box.button(QDialogButtonBox.Ok)
        self.button_ok.setText(translate("OK"))
        self.button_apply = button_box.button(QDialogButtonBox.Apply)
        self.button_apply.setText(translate("Apply"))
        self.button_cancel = button_box.button(QDialogButtonBox.Cancel)
        self.button_cancel.setText(translate("Cancel"))

        button_box.accepted.connect(self.on_ok)
        self.button_apply.clicked.connect(self.on_apply)
        button_box.rejected.connect(self.on_cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addWidget(button_box)

    def on_apply(self):
        try:
            self.model.apply_to_race(self.race_obj)
        except Exception:
            logging.exception("Error applying swimming results")

    def on_ok(self):
        try:
            self.model.apply_to_race(self.race_obj)
        except Exception:
            logging.exception("Error applying swimming results")
        self.accept()

    def on_cancel(self):
        self.reject()
