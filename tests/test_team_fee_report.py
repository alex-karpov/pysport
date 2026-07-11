"""TEMPORARY: render-smoke + structural checks for the fee report templates."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from team_extract_preview import load_sample_race  # noqa: E402
from team_fee_preview import FEE_RACE, VARIANTS, render_fee  # noqa: E402

pytestmark = pytest.mark.skipif(
    not os.path.exists(FEE_RACE),
    reason="fee sample race file not present (data/ is gitignored)",
)


def _html(rel: str) -> str:
    return render_fee(rel, load_sample_race(FEE_RACE))


def test_variant2_renders() -> None:
    html = _html(VARIANTS[0])
    assert "var race" in html
    assert "function buildTable" in html


def test_fee_functions_present() -> None:
    html = _html(VARIANTS[0])
    for token in [
        "[fee-config]",
        "var TARIFF",
        "function parseDays",
        "function startFeeFor",
        "function chipFeeFor",
        "function feeForPerson",
        "function formatMoney",
        "runSelfTest",
    ]:
        assert token in html


def test_variant2_columns() -> None:
    html = _html(VARIANTS[0])
    assert "Взнос" in html
    assert "Комментарий" in html
    assert "Допуск" not in html
    assert "formatDopusk" not in html
    assert "fee-unknown" in html


def test_variant2_summary() -> None:
    html = _html(VARIANTS[0])
    for token in [
        "function buildTeamSummary",
        "function buildSummaryTable",
        "team-summary",
        "summary-host",
        "sum-head",
        "Соревн",
        "Итого",
        "Аренда",
        "sum-total",
    ]:
        assert token in html


def test_variant3_renders() -> None:
    html = _html(VARIANTS[1])
    assert "tariffPerAbsentDay: 55" in html
    assert "tariffPerAbsentDay: 40" in html
    assert "Взнос" in html
    assert "Допуск" not in html


def test_variant2_has_no_absent_tariff() -> None:
    # variant 2 must stay fixed-fee for ЧСФО/ПСФО (no per-absent-day rates in its TARIFF)
    html = _html(VARIANTS[0])
    assert "tariffTotal: 1650" in html
    assert "tariffTotal: 1200" in html
    tariff_block = html.split("var TARIFF = {", 1)[1].split("};", 1)[0]
    assert "tariffPerAbsentDay" not in tariff_block


def test_both_standalone_no_external_refs() -> None:
    for rel in VARIANTS:
        html = _html(rel)
        assert "<script src=" not in html
        assert "<link " not in html
        assert 'src="http' not in html
