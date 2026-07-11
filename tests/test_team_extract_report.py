"""TEMPORARY: render-smoke + structural checks for the team-extracts template."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from team_extract_preview import (  # noqa: E402
    SAMPLE_RACE,
    load_sample_race,
    render_report,
)

pytestmark = pytest.mark.skipif(
    not os.path.exists(SAMPLE_RACE),
    reason="sample race file not present (data/ is gitignored)",
)


def test_renders_without_error():
    html = render_report(load_sample_race())
    assert '<div id="report">' in html
    assert "var race" in html
    assert "function buildTable" in html


def test_contains_transforms_and_selftest():
    html = render_report(load_sample_race())
    assert "function formatZabeg" in html
    assert "function formatDopusk" in html
    assert "runSelfTest" in html


def test_contains_column_headers():
    html = render_report(load_sample_race())
    for label in [
        "№",
        "Фамилия, имя, отчество",
        "Забег",
        "Дата рождения",
        "Группа",
        "Квал",
        "Чип",
        "Допуск",
        "Примечание",
    ]:
        assert label in html
    assert "table-layout: fixed" in html
    assert "chip-dup" in html


def test_first_org_name_present():
    race = load_sample_race()
    orgs = [o for o in race["organizations"] if o.get("name")]
    assert orgs, "sample race has no named organizations"
    assert orgs[0]["name"] in render_report(race)


def test_standalone_no_external_refs():
    html = render_report(load_sample_race())
    assert "<script src=" not in html
    assert "<link " not in html
    assert 'src="http' not in html


def test_page_and_print_rules_present():
    html = render_report(load_sample_race())
    assert "@page" in html
    assert "page-break-after" in html
    assert "ROWS_PER_PAGE" in html
