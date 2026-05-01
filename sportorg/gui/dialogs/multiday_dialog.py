try:
    from PySide6.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QListWidget,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )
except ModuleNotFoundError:
    from PySide2.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QListWidget,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

from sportorg.gui.global_access import GlobalAccess
from sportorg.gui.utils.custom_controls import messageBoxQuestion
from sportorg.language import translate
from sportorg.models.memory import (
    add_race,
    copy_race,
    del_race,
    get_current_race_index,
    move_down_race,
    move_up_race,
    races,
    set_current_race_index,
)
from sportorg.modules.teamwork.teamwork import Teamwork


class MultidayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(GlobalAccess().get_main_window())
        self.setWindowTitle(translate("Multi day"))

        self.layout = QFormLayout(self)
        self.content_layout = QHBoxLayout()
        self.buttons_layout = QVBoxLayout()

        self.item_races = QListWidget()
        self.fill_race_list()
        self.item_races.currentRowChanged.connect(self.select_race)
        self.content_layout.addWidget(self.item_races)

        def add_race_function():
            add_race()
            self.fill_race_list()

        self.item_new = QPushButton(translate("New"))
        self.item_new.clicked.connect(add_race_function)
        self.buttons_layout.addWidget(self.item_new)

        def copy_race_function():
            copy_race()
            self.fill_race_list()

        self.item_copy = QPushButton(translate("Duplicate"))
        self.item_copy.clicked.connect(copy_race_function)
        self.buttons_layout.addWidget(self.item_copy)

        def move_up_race_function():
            if get_current_race_index() <= 0:
                return
            if not self._confirm_day_switch_teamwork_stop():
                return
            move_up_race()
            self.fill_race_list()
            self._refresh_main_window_after_day_switch()

        self.item_move_up = QPushButton(translate("Move up"))
        self.item_move_up.clicked.connect(move_up_race_function)
        self.buttons_layout.addWidget(self.item_move_up)

        def move_down_race_function():
            if get_current_race_index() >= len(races()) - 1:
                return
            if not self._confirm_day_switch_teamwork_stop():
                return
            move_down_race()
            self.fill_race_list()
            self._refresh_main_window_after_day_switch()

        self.item_move_down = QPushButton(translate("Move down"))
        self.item_move_down.clicked.connect(move_down_race_function)
        self.buttons_layout.addWidget(self.item_move_down)

        def del_race_function():
            if len(races()) <= 1:
                return
            if not self._confirm_day_switch_teamwork_stop():
                return
            del_race()
            self.fill_race_list()
            self._refresh_main_window_after_day_switch()

        self.item_del = QPushButton(translate("Delete"))
        self.item_del.clicked.connect(del_race_function)
        self.buttons_layout.addWidget(self.item_del)

        self.buttons_layout.addStretch()
        self.content_layout.addLayout(self.buttons_layout)
        self.layout.addRow(self.content_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_close = button_box.button(QDialogButtonBox.Close)
        self.button_close.setText(translate("Close"))
        self.button_close.clicked.connect(self.close)
        self.layout.addRow(button_box)

    def select_race(self, _index=None):
        index = self.item_races.currentRow()
        if index < 0 or index == get_current_race_index():
            return

        if not self._confirm_day_switch_teamwork_stop():
            self.item_races.blockSignals(True)
            self.item_races.setCurrentRow(get_current_race_index())
            self.item_races.blockSignals(False)
            return

        set_current_race_index(index)
        self._refresh_main_window_after_day_switch()

    def fill_race_list(self):
        race_list = []
        index = get_current_race_index()

        self.item_races.blockSignals(True)
        try:
            self.item_races.clear()
            for cur_race in races():
                race_list.append(
                    cur_race.data.short_title or str(cur_race.data.get_start_datetime())
                )
            self.item_races.addItems(race_list)
            self.item_races.setCurrentRow(index)
        finally:
            self.item_races.blockSignals(False)

    @staticmethod
    def _refresh_main_window_after_day_switch():
        main_window = GlobalAccess().get_main_window()
        main_window.init_model()
        main_window.set_title()

    @staticmethod
    def _confirm_day_switch_teamwork_stop() -> bool:
        if not Teamwork().is_alive():
            return True

        answer = messageBoxQuestion(
            GlobalAccess().get_main_window(),
            translate("Question"),
            translate("Teamwork will be disabled, do you really want to continue?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return False

        Teamwork().stop()
        return True
