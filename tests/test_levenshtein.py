import pytest

from sportorg.common.levenshtein import levenshtein


def test_levenshtein_empty_seqs():
    assert levenshtein("", "") == 0


def test_levenshtein_insert_only():
    assert levenshtein("abc", "") == 3


def test_levenshtein_delete_only():
    assert levenshtein("", "xyz") == 3


def test_levenshtein_replace_only():
    assert levenshtein("abc", "xyz") == 3


def test_levenshtein_mixed_operations():
    assert levenshtein("kitten", "sitting") == 3


@pytest.mark.parametrize(
    "splits, controls, insert_cost, delete_cost, replace_cost, expected_distance",
    [
        ("", "xyz", 2, 1, 1, 6),
        ("abc", "", 1, 2, 1, 6),
        ("abc", "xyz", 1, 1, 1, 3),
        ("abc", "xyz", 2, 1, 1, 3),
        ("abc", "xyz", 1, 1, 3, 6),
        ("abc", "abc", 1, 1, 1, 0),
        ("abxc", "abc", 1, 0, 1, 0),
        ("axc", "abc", 1, 0, 1, 1),
        ("ac", "abc", 1, 0, 1, 1),
    ],
)
def test_levenshtein_with_custom_costs(
    splits, controls, insert_cost, delete_cost, replace_cost, expected_distance
):
    costs = (insert_cost, delete_cost, replace_cost)
    assert levenshtein(splits, controls, *costs) == expected_distance
