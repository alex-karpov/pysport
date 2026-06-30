import pytest
from typing import List

from sportorg.models.memory import (
    Course,
    Group,
    Organization,
    Person,
    Race,
    ResultManual,
    new_event,
    race,
    set_current_race_index,
)


@pytest.fixture
def r() -> Race:
    """Race with 2 courses, 3 groups, 2 orgs, 4 persons, 4 results.

    Layout:
      courses:  [C1, C2]
      groups:   [M21→C1, M35→C2, W21→no course]
      orgs:     [Org1, Org2]
      persons:  [p0(M21/Org1), p1(M21/Org1), p2(M35/Org2), p3(W21/Org1)]
      results:  [res0..res3] mapped 1-to-1 to persons in same order
    """
    new_event([Race()])
    set_current_race_index(0)
    obj = race()

    c1, c2 = Course(), Course()
    c1.name, c2.name = "C1", "C2"
    obj.courses.extend([c1, c2])

    g1, g2, g3 = Group(), Group(), Group()
    g1.name, g2.name, g3.name = "M21", "M35", "W21"
    g1.course, g2.course = c1, c2  # g3 intentionally has no course
    obj.groups.extend([g1, g2, g3])

    o1, o2 = Organization(), Organization()
    o1.name, o2.name = "Org1", "Org2"
    obj.organizations.extend([o1, o2])

    p0, p1, p2, p3 = Person(), Person(), Person(), Person()
    p0.group, p0.organization = g1, o1
    p1.group, p1.organization = g1, o1
    p2.group, p2.organization = g2, o2
    p3.group, p3.organization = g3, o1
    obj.persons.extend([p0, p1, p2, p3])

    for p in obj.persons:
        res = ResultManual()
        res.person = p
        obj.results.append(res)

    return obj


# --- _build_partial ---

def test_build_partial_empty_returns_none(r: Race) -> None:
    assert r._build_partial([]) is None


def test_build_partial_groups_in_model_order(r: Race) -> None:
    # Supply persons from M35 (index 1) then M21 (index 0) — reversed group order
    persons_m35 = [p for p in r.persons if p.group and p.group.name == "M35"]
    persons_m21 = [p for p in r.persons if p.group and p.group.name == "M21"]
    result = r._build_partial(persons_m35 + persons_m21)
    assert result is not None
    group_names = [g["name"] for g in result["groups"]]
    assert group_names == ["M21", "M35"]  # self.groups order, not input order


def test_build_partial_courses_in_model_order(r: Race) -> None:
    # M21→C1 (index 0), M35→C2 (index 1); supply M35 persons first
    persons_m35 = [p for p in r.persons if p.group and p.group.name == "M35"]
    persons_m21 = [p for p in r.persons if p.group and p.group.name == "M21"]
    result = r._build_partial(persons_m35 + persons_m21)
    assert result is not None
    course_names = [c["name"] for c in result["courses"]]
    assert course_names == ["C1", "C2"]  # self.courses order


def test_build_partial_orgs_in_model_order(r: Race) -> None:
    # p2 is in Org2 (index 1), p0 is in Org1 (index 0); supply p2 first
    p0, p2 = r.persons[0], r.persons[2]
    result = r._build_partial([p2, p0])
    assert result is not None
    org_names = [o["name"] for o in result["organizations"]]
    assert org_names == ["Org1", "Org2"]  # self.organizations order


def test_build_partial_results_filtered(r: Race) -> None:
    # Only p0 and p1 (M21) — expect 2 results
    persons_m21 = [p for p in r.persons if p.group and p.group.name == "M21"]
    result = r._build_partial(persons_m21)
    assert result is not None
    assert len(result["results"]) == len(persons_m21)


def test_build_partial_excludes_other_groups(r: Race) -> None:
    persons_m21 = [p for p in r.persons if p.group and p.group.name == "M21"]
    result = r._build_partial(persons_m21)
    assert result is not None
    group_names = [g["name"] for g in result["groups"]]
    assert "M35" not in group_names
    assert "W21" not in group_names


def test_build_partial_group_without_course_excluded_from_courses(r: Race) -> None:
    # W21 has no course → courses list must be empty for W21-only persons
    persons_w21 = [p for p in r.persons if p.group and p.group.name == "W21"]
    result = r._build_partial(persons_w21)
    assert result is not None
    assert result["courses"] == []
