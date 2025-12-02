import pytest
from PySide6.QtCore import Qt

from sportorg.common.otime import OTime
from sportorg.gui.dialogs.swimming_results import (
    PoolTimeConverter,
    SwimmingResultsModel,
    parse_pool_time_str,
)
from sportorg.models.memory import (
    Organization,
    Person,
    Race,
    Result,
    ResultManual,
    ResultStatus,
    race,
)


def test_parse_pool_time_str_basic():
    o = parse_pool_time_str("02:03.45")
    assert o.hour == 0
    assert o.minute == 2
    assert o.sec == 3
    assert o.msec == 450


def test_model_apply_creates_result():
    r = Race()
    race().set_setting("time_accuracy", 2)
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

    row_index = next(i for i, r in enumerate(model._rows) if r["person"].id == p.id)
    idx = model.index(row_index, model.COL_INPUT)
    result = model.setData(idx, "20345", Qt.ItemDataRole.EditRole)
    assert result is True
    # display should reflect formatted value
    idx = model.index(row_index, model.COL_RESULT)
    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "02:03.45"

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
    assert model.setData(idx, "   ", Qt.ItemDataRole.EditRole)
    # display empty for zero
    assert model.data(idx, Qt.ItemDataRole.DisplayRole) == ""

    model.apply_to_race(r)
    res = r.find_person_result(p)
    assert res is not None
    assert res.finish_time.to_msec() == OTime().to_msec()


def test_load_heat_ok_shows_time_and_input_int():
    r = Race()
    race().set_setting("time_accuracy", 2)
    org = Organization()
    org.name = "TeamX"
    r.organizations.append(org)

    p = Person()
    p.name = "John"
    p.surname = "Doe"
    p.set_bib_without_indexing(12)
    p.organization = org
    r.add_person(p)

    # create result with finish time and OK status
    res = ResultManual()
    res.person = p
    res.bib = p.bib
    res.finish_time = parse_pool_time_str("02:03.45")
    res.status = ResultStatus.OK
    r.add_result(res)

    model = SwimmingResultsModel([p], {p.id: res}, parent=None)
    row_index = next(i for i, r in enumerate(model._rows) if r["person"].id == p.id)
    idx_input = model.index(row_index, model.COL_INPUT)
    idx_result = model.index(row_index, model.COL_RESULT)
    assert model.data(idx_input, Qt.ItemDataRole.DisplayRole) == str(
        PoolTimeConverter.result_to_input(res)
    )
    assert model.data(idx_result, Qt.ItemDataRole.DisplayRole) == "02:03.45"


def test_load_heat_non_ok_shows_status():
    r = Race()
    org = Organization()
    org.name = "TeamX"
    r.organizations.append(org)

    p = Person()
    p.name = "Jane"
    p.surname = "Doe"
    p.set_bib_without_indexing(23)
    p.organization = org
    r.add_person(p)

    res = ResultManual()
    res.person = p
    res.bib = p.bib
    res.finish_time = OTime()
    res.status = ResultStatus.DID_NOT_START
    res.status_comment = "DNS"
    r.add_result(res)

    model = SwimmingResultsModel([p], {p.id: res}, parent=None)
    row_index = next(i for i, r in enumerate(model._rows) if r["person"].id == p.id)
    idx_input = model.index(row_index, model.COL_INPUT)
    idx_result = model.index(row_index, model.COL_RESULT)
    assert model.data(idx_input, Qt.ItemDataRole.DisplayRole) == "DNS"
    assert model.data(idx_result, Qt.ItemDataRole.DisplayRole) == "DNS"


def test_input_dns_sets_result_status():
    r = Race()
    org = Organization()
    org.name = "TeamX"
    r.organizations.append(org)

    p = Person()
    p.name = "Rick"
    p.surname = "Doe"
    p.set_bib_without_indexing(45)
    p.organization = org
    r.add_person(p)

    model = SwimmingResultsModel([p], {}, parent=None)
    row_index = next(i for i, r in enumerate(model._rows) if r["person"].id == p.id)
    idx_input = model.index(row_index, model.COL_INPUT)
    assert model.setData(idx_input, "dns", Qt.ItemDataRole.EditRole)
    model.apply_to_race(r)
    res = r.find_person_result(p)
    assert res is not None
    assert res.status == ResultStatus.DID_NOT_START
    assert res.status_comment == "DNS"
    assert (
        res.finish_time.to_msec() == OTime(hour=23, minute=59, sec=59, msec=0).to_msec()
    )


def test_input_time_sets_ok_status_and_finish():
    r = Race()
    p = Person()
    p.set_bib_without_indexing(77)
    r.add_person(p)

    model = SwimmingResultsModel([p], {}, parent=None)
    row_index = next(i for i, r in enumerate(model._rows) if r["person"].id == p.id)
    idx_input = model.index(row_index, model.COL_INPUT)
    assert model.setData(idx_input, "01:20.50", Qt.ItemDataRole.EditRole)
    model.apply_to_race(r)
    res = r.find_person_result(p)
    assert res is not None
    assert res.status == ResultStatus.OK
    assert res.finish_time.to_msec() == parse_pool_time_str("01:20.50").to_msec()
