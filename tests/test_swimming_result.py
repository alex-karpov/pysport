import pytest

from sportorg.common.otime import OTime
from sportorg.gui.dialogs.swimming_results import PoolTimeConverter


@pytest.mark.parametrize(
    "otime, expected_input",
    [
        (OTime(hour=0, minute=0, sec=0, msec=0), 0),
        (OTime(hour=0, minute=0, sec=56, msec=780), 5678),
        (OTime(hour=0, minute=1, sec=23, msec=450), 12345),
        (OTime(hour=1, minute=2, sec=3, msec=456), 1020345),
        (OTime(hour=0, minute=59, sec=59, msec=999), 595999),
        (OTime(hour=23, minute=59, sec=59, msec=999), 23595999),
        (OTime(hour=12, minute=34, sec=56, msec=789), 12345678),
        (None, 0),
    ],
)
def test_otime_to_input(otime, expected_input):
    result = PoolTimeConverter.otime_to_input(otime)
    assert result == expected_input


@pytest.mark.parametrize(
    "input, expected_otime",
    [
        (0, OTime(hour=0, minute=0, sec=0, msec=0)),
        (5678, OTime(hour=0, minute=0, sec=56, msec=780)),
        (12345, OTime(hour=0, minute=1, sec=23, msec=450)),
        (1020345, OTime(hour=1, minute=2, sec=3, msec=450)),
        (595999, OTime(hour=0, minute=59, sec=59, msec=990)),
        (23595999, OTime(hour=23, minute=59, sec=59, msec=990)),
        (12345678, OTime(hour=12, minute=34, sec=56, msec=780)),
    ],
)
def test_input_to_otime(input, expected_otime):
    result = PoolTimeConverter.inout_to_otime(input)
    assert result == expected_otime


@pytest.mark.parametrize(
    "input, expected_str",
    [
        (0, "00:00.00"),
        (5678, "00:56.78"),
        (12345, "01:23.45"),
        (1020345, "62:03.45"),
        (595999, "59:59.99"),
        (23595999, "1439:59.99"),
        (12345678, "754:56.78"),
    ],
)
def test_input_to_str(input, expected_str):
    result = PoolTimeConverter.input_to_str(input)
    assert result == expected_str
