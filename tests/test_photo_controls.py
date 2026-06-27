"""Tests for rogaine photo-control merging into read chips."""

from sportorg.common.otime import OTime
from sportorg.models.memory import (
    Group,
    Person,
    Race,
    ResultSportident,
    Split,
    new_event,
    race,
)
from sportorg.models.result.photo_controls import (
    append_photo_controls,
    is_photo_mark,
    load_team_controls,
)

START = OTime(hour=10)


def make_result(bib):
    group = Group()
    person = Person()
    person.group = group
    person.set_bib(bib)
    person.start_time = START
    result = ResultSportident()
    result.person = person
    new_event([Race()])
    race().groups.append(group)
    race().persons.append(person)
    race().results.append(result)
    return result


def make_split(code, time):
    split = Split()
    split.code = str(code)
    split.time = time
    return split


def test_is_photo_mark():
    assert is_photo_mark(make_split("31", START), START)
    assert is_photo_mark(make_split("31", OTime(hour=10, sec=1)), START)
    assert not is_photo_mark(make_split("31", OTime(hour=10, sec=2)), START)
    assert not is_photo_mark(make_split("31", OTime(hour=10, minute=30)), START)


def test_load_team_controls(tmp_path):
    csv_file = tmp_path / "controls.csv"
    csv_file.write_text("x;12;31\nx;12;32\nx;13;41\n", encoding="utf-8")

    assert load_team_controls(str(csv_file)) == {12: ["31", "32"], 13: ["41"]}


def test_load_team_controls_skips_short_or_bad_rows(tmp_path):
    csv_file = tmp_path / "controls.csv"
    csv_file.write_text("x;12\nx;notanumber;31\nx;12;33\n", encoding="utf-8")

    assert load_team_controls(str(csv_file)) == {12: ["33"]}


def test_append_adds_missing():
    result = make_result(bib=123)

    added = append_photo_controls(result, {12: ["31", "32"]})

    assert added == 2
    assert [s.code for s in result.splits] == ["31", "32"]
    assert all(s.time == START for s in result.splits)


def test_append_is_idempotent():
    result = make_result(bib=123)
    team_controls = {12: ["31", "32"]}

    append_photo_controls(result, team_controls)
    added_again = append_photo_controls(result, team_controls)

    assert added_again == 0
    assert [s.code for s in result.splits] == ["31", "32"]


def test_real_punch_does_not_suppress_photo_mark():
    result = make_result(bib=123)
    result.splits = [make_split("31", OTime(hour=10, minute=30))]

    added = append_photo_controls(result, {12: ["31"]})

    assert added == 1
    assert [s.code for s in result.splits] == ["31", "31"]


def test_existing_photo_mark_suppresses():
    result = make_result(bib=123)
    result.splits = [make_split("31", START)]

    added = append_photo_controls(result, {12: ["31", "32"]})

    assert added == 1
    assert sorted(s.code for s in result.splits) == ["31", "32"]


def test_dedup_within_one_second_of_start():
    result = make_result(bib=123)
    result.splits = [make_split("31", OTime(hour=10, sec=1))]

    added = append_photo_controls(result, {12: ["31"]})

    assert added == 0


def test_no_bib_is_skipped():
    result = make_result(bib=0)

    added = append_photo_controls(result, {0: ["31"]})

    assert added == 0
    assert result.splits == []
