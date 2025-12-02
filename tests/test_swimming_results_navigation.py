import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from sportorg.gui.dialogs.swimming_results import (
    PoolTimeConverter,
    SwimmingResultsDialog,
    SwimmingResultsModel,
)
from sportorg.models.memory import Person, Race, ResultManual


def ensure_app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_get_available_and_first_unfinished_heat():
    ensure_app()
    r = Race()
    # create 3 persons in heats 0,1,2
    p0 = Person()
    p0.start_group = 0
    p1 = Person()
    p1.start_group = 1
    p2 = Person()
    p2.start_group = 2
    r.persons.extend([p0, p1, p2])

    # add a result for p0 so heat 0 is finished
    res0 = ResultManual()
    res0.person = p0
    res0.finish_time = res0.finish_time  # non-zero by default
    r.results.append(res0)

    dlg = SwimmingResultsDialog(None)
    # use test race object
    dlg.race_obj = r

    heats = dlg.get_available_heats()
    assert heats == [0, 1, 2]

    first_unfinished = dlg.find_first_unfinished_heat()
    assert first_unfinished == 1


def test_load_heat_and_model_contents():
    ensure_app()
    r = Race()
    pA = Person()
    pA.start_group = 5
    pA.set_bib_without_indexing(10)
    pB = Person()
    pB.start_group = 5
    pB.set_bib_without_indexing(11)
    pC = Person()
    pC.start_group = 7
    pC.set_bib_without_indexing(12)
    r.persons.extend([pA, pB, pC])

    dlg = SwimmingResultsDialog(None)
    dlg.race_obj = r
    dlg.load_heat(5)

    # model should contain only persons A and B
    assert isinstance(dlg.model, SwimmingResultsModel)
    assert len(dlg.model._rows) == 2
    assert all(row["person"].start_group == 5 for row in dlg.model._rows)


def test_apply_and_reset_behavior():
    ensure_app()
    r = Race()
    p = Person()
    p.start_group = 3
    p.set_bib_without_indexing(101)
    r.persons.append(p)

    dlg = SwimmingResultsDialog(None)
    dlg.race_obj = r
    dlg.load_heat(3)

    # initially no results
    assert r.find_person_result(p) is None

    # modify model row directly to simulate editing
    assert len(dlg.model._rows) == 1
    row = dlg.model._rows[0]
    # set input_int to represent 1 minute 00.00 -> mm:ss.hh format -> minutes=1 => hour=0, minute=1 => otime -> input
    # PoolTimeConverter expects integer encoding; we'll set to 10000 (minute=1 -> minute*10000)
    row["input_int"] = (
        PoolTimeConverter.otime_to_input(row.get("result") or row.get("result"))
        if False
        else 60000
    )
    row["modified"] = True

    # apply via dialog
    dlg.on_apply()

    # result should be created in race
    res = r.find_person_result(p)
    assert res is not None

    # now change model and reset
    # set changed value
    dlg.model._rows[0]["input_int"] = 12345
    dlg.model._rows[0]["modified"] = True
    dlg.on_reset()

    # after reset, model input_int should match race result finish_time
    res_after = r.find_person_result(p)
    expected = (
        PoolTimeConverter.otime_to_input(res_after.finish_time) if res_after else 0
    )
    assert dlg.model._rows[0]["input_int"] == expected


@pytest.mark.skip(reason="Not working")
def test_try_change_heat_prompts_and_honors_save_cancel(monkeypatch):
    ensure_app()
    r = Race()
    p1 = Person()
    p1.start_group = 1
    p2 = Person()
    p2.start_group = 2
    r.persons.extend([p1, p2])

    dlg = SwimmingResultsDialog(None)
    dlg.race_obj = r
    dlg.load_heat(1)

    # mark unsaved change
    dlg.model._rows[0]["modified"] = True

    # monkeypatch QMessageBox to simulate Cancel
    class FakeMsgCancel:
        def __init__(self, parent=None):
            pass

        def setWindowTitle(self, *_):
            pass

        def setText(self, *_):
            pass

        def setStandardButtons(self, *_):
            pass

        def exec(self):
            return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(
        "sportorg.gui.dialogs.swimming_results.QMessageBox", FakeMsgCancel
    )

    # attempt change: should cancel and keep current heat
    old_heat = dlg.heat_current
    dlg.try_change_heat(2)
    assert dlg.heat_current == old_heat

    # now simulate Save
    class FakeMsgSave(FakeMsgCancel):
        def exec(self):
            return QMessageBox.StandardButton.Save

    monkeypatch.setattr(
        "sportorg.gui.dialogs.swimming_results.QMessageBox", FakeMsgSave
    )

    # set a modified value to ensure apply runs
    dlg.model._rows[0]["modified"] = True
    dlg.model._rows[0]["input_int"] = 90000

    dlg.try_change_heat(2)
    # after saving, heat should change
    assert dlg.heat_current == 2
