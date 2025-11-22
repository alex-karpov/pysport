from PySide6.QtCore import Qt

from sportorg.common.otime import OTime
from sportorg.gui.dialogs.swimming_results import (
    SwimmingResultsModel,
    parse_pool_time_str,
)
from sportorg.models.memory import Organization, Person, Race


def test_parse_pool_time_str_basic():
    o = parse_pool_time_str("02:03.45")
    assert o.hour == 0
    assert o.minute == 2
    assert o.sec == 3
    assert o.msec == 450


def test_model_apply_creates_result():
    r = Race()
    org = Organization()
    org.name = "TeamX"
    r.organizations.append(org)

    p = Person()
    p.name = "John"
    p.surname = "Doe"
    p.set_bib_without_indexing(12)
    p.organization = org

    # add person to local race (indexes in that race)
    r.add_person(p)

    model = SwimmingResultsModel([p], {}, parent=None)

    idx = model.index(0, 0)
    assert model.setData(idx, "02:03.45", Qt.EditRole)
    # display should reflect formatted value
    assert model.data(idx, Qt.DisplayRole) == "02:03.45"

    model.apply_to_race(r)

    res = r.find_person_result(p)
    assert res is not None
    assert res.finish_time.to_msec() == parse_pool_time_str("02:03.45").to_msec()


def test_empty_input_sets_zero_time():
    r = Race()
    p = Person()
    p.set_bib_without_indexing(99)
    r.add_person(p)

    model = SwimmingResultsModel([p], {}, parent=None)
    idx = model.index(0, 0)
    assert model.setData(idx, "   ", Qt.EditRole)
    # display empty for zero
    assert model.data(idx, Qt.DisplayRole) == ""

    model.apply_to_race(r)
    res = r.find_person_result(p)
    assert res is not None
    assert res.finish_time.to_msec() == OTime().to_msec()
