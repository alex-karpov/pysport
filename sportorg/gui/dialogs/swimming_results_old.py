import logging
from dataclasses import dataclass
from itertools import zip_longest
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from sportorg.common.otime import OTime
from sportorg.gui.global_access import GlobalAccess
from sportorg.language import translate
from sportorg.models.memory import Person, Result, race

HEADER_LSPACER = 0
HEADER_PREV = 1
HEADER_EDITBOX = 2
HEADER_NEXT = 3
HEADER_RSPACER = 4


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


class ResultLineEdit(QLineEdit):
    pass


class HeatLineEdit(QLineEdit):
    def __init__(self, bottom: int, top: int, parent=None):
        super().__init__(parent)
        self.setValidator(QIntValidator(bottom, top, self))

    def get_value(self):
        text = self.text()
        return int(text) if text else None

    def set_value(self, value):
        if isinstance(value, int) and value >= 0:
            self.setText(str(value))
        else:
            raise ValueError("Value should be int")


@dataclass
class Competitor:
    bib: int = 0
    person: Person = None
    result: Result = None
    result_input: int = 0


@dataclass
class LaneView:
    lane_number_widget: QLabel
    time_input: ResultLineEdit
    result: QLabel
    bib: QLabel
    person_name: QLabel
    person_team: QLabel
    lane_number: int = 0

    def __init__(self, lane_number: int = 0, competitor: Competitor = None):
        super().__init__()
        self.lane_number = lane_number
        self.init()
        self.fill(competitor)

    def init(self):
        self.lane_number_widget = QLabel(str(self.lane_number))
        self.time_input = ResultLineEdit()
        self.result = QLabel()
        self.bib = QLabel()
        self.person_name = QLabel()
        self.person_team = QLabel()
        self.clear()

    def fill(self, competitor: Competitor = None):
        if competitor:
            self.time_input.setText(str(competitor.result_input))
            self.result.setText(PoolTimeConverter.input_to_str(competitor.result_input))
            self.bib.setText(str(competitor.bib))
            self.person_name.setText(competitor.person.full_name)
            self.person_team.setText(competitor.person.organization.name)

    def clear(self):
        self.time_input.setText("0")
        self.result.setText(PoolTimeConverter.input_to_str(0))
        self.bib.setText("0")
        self.person_name.setText("")
        self.person_team.setText("")

    def hide(self):
        self.lane_number_widget.hide()
        self.time_input.hide()
        self.result.hide()
        self.bib.hide()
        self.person_name.hide()
        self.person_team.hide()

    def show(self):
        self.lane_number_widget.show()
        self.time_input.show()
        self.result.show()
        self.bib.show()
        self.person_name.show()
        self.person_team.show()


class PoolData(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if not isinstance(key, int):
                raise ValueError("Key should be int")
            if not isinstance(value, list):
                raise ValueError("Value should be list")
            if not not all(isinstance(item, Competitor) for item in value):
                raise ValueError("Value should be list of Competitor")

    def get_min_heat_number(self) -> int:
        return min(self.keys())

    def get_max_heat_number(self) -> int:
        return max(self.keys())

    def get_next_heat_number(self, current: int) -> Optional[int]:
        heat_numbers = sorted(self.keys())
        try:
            index = heat_numbers.index(current)
            return heat_numbers[index + 1]
        except ValueError:
            return None
        except IndexError:
            return None

    def get_prev_heat_number(self, current: int) -> Optional[int]:
        heat_numbers = sorted(self.keys())
        try:
            index = heat_numbers.index(current)
            if index == 0:
                return None
            return heat_numbers[index - 1]
        except ValueError:
            return None
        except IndexError:
            return None


class SwimmingResultsDialog(QDialog):
    pool_data: PoolData
    pool_lanes: List[LaneView]
    current_heat: int

    def __init__(self):
        super().__init__(GlobalAccess().get_main_window())
        self.pool_data = PoolData()
        self.pool_lanes = []
        self.time_format = "hh:mm:ss"

    def exec_(self):
        self.populate_pool_data()
        self.current_heat = self.pool_data.get_min_heat_number()
        self.init_ui()
        return super().exec_()

    def init_ui(self):
        # self.setFixedWidth(500)
        self.setWindowTitle(translate("Swimming Results"))
        self.setSizeGripEnabled(False)
        self.setModal(True)

        self.layout = QVBoxLayout(self)

        self.create_navbar_ui()
        self.create_pool_lanes_ui()
        self.create_buttons_ui()

        self.refresh_ui()

        self.show()

    def create_navbar_ui(self):
        self.header = QGridLayout()

        min_heat = self.pool_data.get_min_heat_number()
        max_heat = self.pool_data.get_max_heat_number()

        self.heat_number_layout = QHBoxLayout()
        self.heat_number_edit = HeatLineEdit(min_heat, max_heat)
        self.heat_number_edit.set_value(self.current_heat)
        self.heat_number_edit.returnPressed.connect(self.apply_heat_number_edit)
        self.heat_number_layout.addWidget(self.heat_number_edit)
        self.heat_number_max_label = QLabel(" / ")
        self.heat_number_layout.addWidget(self.heat_number_max_label)
        self.header.addLayout(self.heat_number_layout, 0, HEADER_EDITBOX)

        self.prev_heat_button = QPushButton("<")
        self.prev_heat_button.pressed.connect(self.go_to_prev_heat)
        self.header.addWidget(self.prev_heat_button, 0, HEADER_PREV)
        self.next_heat_button = QPushButton(">")
        self.next_heat_button.pressed.connect(self.go_to_next_heat)
        self.header.addWidget(self.next_heat_button, 0, HEADER_NEXT)

        self.set_navbar_ui_style()

        self.layout.addLayout(self.header)

    def set_navbar_ui_style(self):
        side_column_min_size = 1
        side_column_stretch = 100
        self.header.setColumnMinimumWidth(HEADER_LSPACER, side_column_min_size)
        self.header.setColumnStretch(HEADER_LSPACER, side_column_stretch)
        self.header.setColumnMinimumWidth(HEADER_RSPACER, side_column_min_size)
        self.header.setColumnStretch(HEADER_RSPACER, side_column_stretch)

        font_size = 20
        heat_number_edit_font = self.heat_number_edit.font()
        heat_number_edit_font.setBold(True)
        heat_number_edit_font.setPointSize(font_size)
        self.heat_number_edit.setFont(heat_number_edit_font)
        self.heat_number_edit.setFixedWidth(70)
        self.heat_number_edit.setAlignment(Qt.AlignHCenter)

        self.heat_number_layout.setAlignment(Qt.AlignHCenter)

        heat_button_width = 70
        self.prev_heat_button.setFixedWidth(heat_button_width)
        self.next_heat_button.setFixedWidth(heat_button_width)

    def set_lanes_style(self):
        font_size = 16
        for lane_view in self.pool_lanes:
            lane_number_font = lane_view.lane_number_widget.font()
            lane_number_font.setBold(True)
            lane_number_font.setPointSize(font_size)
            lane_view.lane_number_widget.setFont(lane_number_font)

            time_input_font = lane_view.time_input.font()
            time_input_font.setPointSize(font_size)
            lane_view.time_input.setFont(time_input_font)
            lane_view.time_input.setFixedWidth(75)
            lane_view.time_input.setAlignment(Qt.AlignRight)

            result_font = lane_view.result.font()
            result_font.setPointSize(font_size)
            lane_view.result.setFont(result_font)

            self.pool_grid_layout.setColumnStretch(5, 100)

    def create_pool_lanes_ui(self):
        self.pool_grid_layout = QGridLayout()
        self.layout.addLayout(self.pool_grid_layout)
        self.add_lanes(6)
        self.set_lanes_style()

    def create_buttons_ui(self):
        def cancel_changes():
            self.close()

        def apply_changes():
            try:
                self.apply_changes_impl()
            except Exception as e:
                logging.error(str(e))
            self.close()

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        self.button_ok = button_box.button(QDialogButtonBox.Ok)
        self.button_ok.setText(translate("OK"))
        self.button_ok.clicked.connect(apply_changes)
        # self.button_ok.clicked.disconnect()
        self.button_apply = button_box.button(QDialogButtonBox.Apply)
        self.button_apply.setText(translate("Apply"))
        self.button_apply.clicked.connect(apply_changes)
        self.button_cancel = button_box.button(QDialogButtonBox.Cancel)
        self.button_cancel.setText(translate("Cancel"))
        self.button_cancel.clicked.connect(cancel_changes)

        self.layout.addWidget(button_box)

    def refresh_ui(self):
        self.refresh_header_ui()

        heat_swimmers = self.pool_data.get(self.current_heat, [])
        for lane, person in zip_longest(self.pool_lanes, heat_swimmers, fillvalue=None):
            self.refresh_lane_ui(lane, person)

    def refresh_header_ui(self):
        self.heat_number_edit.set_value(self.current_heat)

        max_heat_number = self.pool_data.get_max_heat_number()
        self.heat_number_max_label.setText(f" / {max_heat_number}")

        prev_heat_number = self.pool_data.get_prev_heat_number(self.current_heat)
        label = "<" if prev_heat_number is None else f"{prev_heat_number} <"
        self.prev_heat_button.setText(label)
        self.prev_heat_button.setEnabled(prev_heat_number is not None)

        next_heat_number = self.pool_data.get_next_heat_number(self.current_heat)
        label = ">" if next_heat_number is None else f"> {next_heat_number}"
        self.next_heat_button.setText(label)
        self.next_heat_button.setEnabled(next_heat_number is not None)

    def refresh_lane_ui(self, lane_view: LaneView = None, person: Competitor = None):
        if lane_view is None:
            lane_view = LaneView()
            self.add_lane_view(lane_view)

        if person is None:
            lane_view.clear()
            pass
        else:
            lane_view.fill(person)
            # lane_view.show()

    def add_lanes(self, num_lanes: int = 0) -> List[LaneView]:
        """
        Creates and initializes a list of LaneView objects for the pool lanes.
        """
        for i in range(num_lanes):
            lane_view = LaneView(lane_number=i + 1)
            self.add_lane_view(lane_view)

    def add_lane_view(self, lane_view: LaneView):
        grid_layout = self.pool_grid_layout
        row = len(self.pool_lanes)
        self.pool_lanes.append(lane_view)

        grid_layout.addWidget(lane_view.lane_number_widget, row, 0)
        grid_layout.addWidget(lane_view.time_input, row, 1)
        grid_layout.addWidget(lane_view.result, row, 2)
        grid_layout.addWidget(lane_view.bib, row, 3)
        grid_layout.addWidget(lane_view.person_name, row, 4)
        grid_layout.addWidget(lane_view.person_team, row, 5)

    def populate_pool_data(self):
        obj = race()
        self.pool_data = PoolData()

        results = {result.person.id: result for result in obj.results if result.person}
        for person in obj.persons:
            result = results.get(person.id, None)
            finish_otime = result.finish_time if result else OTime()
            result_input = PoolTimeConverter.otime_to_input(finish_otime)
            heat_number = person.start_group
            competitor = Competitor(
                bib=person.bib,
                person=person,
                result=result,
                result_input=result_input,
            )
            heat_data = self.pool_data.get(heat_number, [])
            heat_data.append(competitor)
            self.pool_data[heat_number] = heat_data

        for heat in self.pool_data.values():
            heat.sort(key=lambda person: person.bib)

    def apply_heat_number_edit(self):
        heat_number = self.heat_number_edit.get_value()
        self.change_heat_number(heat_number)
        self.refresh_ui()

    def go_to_prev_heat(self):
        new_heat_number = self.pool_data.get_prev_heat_number(self.current_heat)
        if new_heat_number:
            self.change_heat_number(new_heat_number)
        self.refresh_ui()

    def go_to_next_heat(self):
        new_heat_number = self.pool_data.get_next_heat_number(self.current_heat)
        if new_heat_number:
            self.change_heat_number(new_heat_number)
        self.refresh_ui()

    def change_heat_number(self, new_heat_no: int):
        if new_heat_no not in self.pool_data:
            new_heat_no = self.current_heat
        self.current_heat = new_heat_no

    def apply_changes_impl(self):
        obj = race()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)
