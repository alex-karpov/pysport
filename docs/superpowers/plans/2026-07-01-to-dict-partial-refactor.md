# to_dict_partial Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Race.to_dict_partial` with five named methods (`partial_for_*`) and a private `_build_partial` helper, eliminating implicit dispatch, caller mutation, string-based group lookup, and missing type hints.

**Architecture:** `_build_partial(persons)` contains all output-building logic; each public `partial_for_*` method resolves its input to an ordered `List[Person]` (in `self.persons` order) and delegates. `report_dialog.py` calls the appropriate method per active tab.

**Tech Stack:** Python 3.8, PySide6, mypy strict, pytest, `uv run poe`

## Global Constraints

- Python 3.8 syntax only — no walrus operator, no `X | Y` union types (use `Optional[X]`), no `list[X]` lowercase generics (use `List[X]` from `typing`)
- Type hints required on all new functions (mypy strict: `disallow_untyped_defs = true`)
- All work in worktree `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-to-dict-partial`, branch `ank/to-dict-partial`
- Run all commands from the worktree root
- Commit message format: `<type>(<scope>): <summary>` — present tense, ≤70 chars, no period
- Output dict format must remain unchanged (template backward compatibility)

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `sportorg/models/memory.py` | Modify | Add `_build_partial` + 5 `partial_for_*` methods; delete `to_dict_partial` |
| `sportorg/gui/dialogs/report_dialog.py` | Modify | Replace 5 `to_dict_partial(...)` call sites with named methods |
| `tests/test_race_partial.py` | Create | Tests for all new methods |

---

## Task 1: `_build_partial` — tests and implementation

**Files:**
- Create: `tests/test_race_partial.py`
- Modify: `sportorg/models/memory.py` (~line 1735, just before `to_dict_partial`)

**Interfaces:**
- Produces: `Race._build_partial(self, persons: List[Person]) -> Optional[Dict[str, Any]]`

- [ ] **Step 1: Create the test file with fixture and `_build_partial` tests**

```python
# tests/test_race_partial.py
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
```

- [ ] **Step 2: Run tests to confirm they all fail (method not yet defined)**

```
cd C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-to-dict-partial
uv run pytest tests/test_race_partial.py -vv
```

Expected: `AttributeError: 'Race' object has no attribute '_build_partial'` (all tests fail)

- [ ] **Step 3: Implement `_build_partial` in `memory.py`**

Add the method inside the `Race` class, immediately before `to_dict_partial` (~line 1735).  
Insert after the closing brace of `to_dict`:

```python
    def _build_partial(
        self, persons: List[Person]
    ) -> Optional[Dict[str, Any]]:
        if not persons:
            return None
        person_set = set(persons)
        person_groups = {p.group for p in persons if p.group}
        person_orgs = {p.organization for p in persons if p.organization}
        return_groups = [g for g in self.groups if g in person_groups]
        group_courses = {g.course for g in return_groups if g.course}
        return_courses = [c for c in self.courses if c in group_courses]
        return_orgs = [o for o in self.organizations if o in person_orgs]
        return_results = [r for r in self.results if r.person in person_set]
        return {
            "object": self.__class__.__name__,
            "id": str(self.id),
            "data": self.data.to_dict(),
            "settings": self.settings.copy(),
            "organizations": [item.to_dict() for item in return_orgs],
            "courses": [item.to_dict() for item in return_courses],
            "groups": [item.to_dict() for item in return_groups],
            "results": [item.to_dict() for item in return_results],
            "persons": [item.to_dict() for item in persons],
        }
```

- [ ] **Step 4: Run tests to confirm they all pass**

```
uv run pytest tests/test_race_partial.py -vv -k "build_partial"
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```
git add tests/test_race_partial.py sportorg/models/memory.py
git commit -m "refactor(report): add Race._build_partial helper with tests"
```

---

## Task 2: Five public resolver methods — tests and implementation

**Files:**
- Modify: `tests/test_race_partial.py` (append tests)
- Modify: `sportorg/models/memory.py` (add methods after `_build_partial`)

**Interfaces:**
- Consumes: `Race._build_partial(persons: List[Person]) -> Optional[Dict[str, Any]]`
- Produces:
  - `Race.partial_for_persons(self, persons: List[Person]) -> Optional[Dict[str, Any]]`
  - `Race.partial_for_groups(self, groups: List[Group]) -> Optional[Dict[str, Any]]`
  - `Race.partial_for_courses(self, courses: List[Course]) -> Optional[Dict[str, Any]]`
  - `Race.partial_for_orgs(self, orgs: List[Organization]) -> Optional[Dict[str, Any]]`
  - `Race.partial_for_results(self, results: List[Result]) -> Optional[Dict[str, Any]]`

- [ ] **Step 1: Append tests for the five public methods to `test_race_partial.py`**

```python
# --- partial_for_persons ---

def test_partial_for_persons_empty_returns_none(r: Race) -> None:
    assert r.partial_for_persons([]) is None


def test_partial_for_persons_reorders_by_model(r: Race) -> None:
    # Reverse the persons list — output must follow self.persons order
    reversed_persons = list(reversed(r.persons))
    result = r.partial_for_persons(reversed_persons)
    assert result is not None
    expected = [str(p.id) for p in r.persons]
    actual = [p["id"] for p in result["persons"]]
    assert actual == expected


def test_partial_for_persons_subset(r: Race) -> None:
    # Supply only p0 and p2 — output persons must be exactly those two
    selected = [r.persons[0], r.persons[2]]
    result = r.partial_for_persons(selected)
    assert result is not None
    assert len(result["persons"]) == 2


# --- partial_for_groups ---

def test_partial_for_groups_empty_returns_none(r: Race) -> None:
    assert r.partial_for_groups([]) is None


def test_partial_for_groups_filters_persons(r: Race) -> None:
    g_m21 = r.groups[0]  # M21 — has p0, p1
    result = r.partial_for_groups([g_m21])
    assert result is not None
    assert len(result["persons"]) == 2
    assert len(result["groups"]) == 1
    assert result["groups"][0]["name"] == "M21"


def test_partial_for_groups_order_follows_model(r: Race) -> None:
    # Select W21 (index 2) and M21 (index 0) in that order
    g_w21, g_m21 = r.groups[2], r.groups[0]
    result = r.partial_for_groups([g_w21, g_m21])
    assert result is not None
    group_names = [g["name"] for g in result["groups"]]
    assert group_names == ["M21", "W21"]  # self.groups order


def test_partial_for_groups_excludes_other_persons(r: Race) -> None:
    g_m21 = r.groups[0]
    result = r.partial_for_groups([g_m21])
    assert result is not None
    person_ids = {p["id"] for p in result["persons"]}
    expected_ids = {str(p.id) for p in r.persons if p.group == g_m21}
    assert person_ids == expected_ids


# --- partial_for_courses ---

def test_partial_for_courses_empty_returns_none(r: Race) -> None:
    assert r.partial_for_courses([]) is None


def test_partial_for_courses_filters_by_course(r: Race) -> None:
    # C1 → M21 only
    result = r.partial_for_courses([r.courses[0]])
    assert result is not None
    group_names = [g["name"] for g in result["groups"]]
    assert group_names == ["M21"]


def test_partial_for_courses_multi(r: Race) -> None:
    # Both courses → M21 and M35 (W21 has no course, excluded)
    result = r.partial_for_courses(r.courses)
    assert result is not None
    group_names = [g["name"] for g in result["groups"]]
    assert "M21" in group_names
    assert "M35" in group_names
    assert "W21" not in group_names


# --- partial_for_orgs ---

def test_partial_for_orgs_empty_returns_none(r: Race) -> None:
    assert r.partial_for_orgs([]) is None


def test_partial_for_orgs_filters_persons(r: Race) -> None:
    o2 = r.organizations[1]  # Org2 — only p2
    result = r.partial_for_orgs([o2])
    assert result is not None
    assert len(result["persons"]) == 1


def test_partial_for_orgs_multi(r: Race) -> None:
    # Both orgs → all 4 persons
    result = r.partial_for_orgs(r.organizations)
    assert result is not None
    assert len(result["persons"]) == len(r.persons)


# --- partial_for_results ---

def test_partial_for_results_empty_returns_none(r: Race) -> None:
    assert r.partial_for_results([]) is None


def test_partial_for_results_persons_in_model_order(r: Race) -> None:
    # Results in reversed order — output persons must follow self.persons order
    reversed_results = list(reversed(r.results))
    result = r.partial_for_results(reversed_results)
    assert result is not None
    expected = [str(p.id) for p in r.persons]
    actual = [p["id"] for p in result["persons"]]
    assert actual == expected


def test_partial_for_results_subset(r: Race) -> None:
    # Pass only first result — output has exactly 1 person
    result = r.partial_for_results([r.results[0]])
    assert result is not None
    assert len(result["persons"]) == 1
```

- [ ] **Step 2: Run tests to confirm new tests fail**

```
uv run pytest tests/test_race_partial.py -vv -k "partial_for"
```

Expected: `AttributeError: 'Race' object has no attribute 'partial_for_persons'` (all 19 new tests fail)

- [ ] **Step 3: Implement the five public methods in `memory.py`**

Add these five methods inside the `Race` class, immediately after `_build_partial`:

```python
    def partial_for_persons(
        self, persons: List[Person]
    ) -> Optional[Dict[str, Any]]:
        persons_set = set(persons)
        ordered = [p for p in self.persons if p in persons_set]
        return self._build_partial(ordered)

    def partial_for_groups(
        self, groups: List[Group]
    ) -> Optional[Dict[str, Any]]:
        groups_set = set(groups)
        ordered = [p for p in self.persons if p.group in groups_set]
        return self._build_partial(ordered)

    def partial_for_courses(
        self, courses: List[Course]
    ) -> Optional[Dict[str, Any]]:
        courses_set = set(courses)
        groups_set = {g for g in self.groups if g.course in courses_set}
        ordered = [p for p in self.persons if p.group in groups_set]
        return self._build_partial(ordered)

    def partial_for_orgs(
        self, orgs: List[Organization]
    ) -> Optional[Dict[str, Any]]:
        orgs_set = set(orgs)
        ordered = [p for p in self.persons if p.organization in orgs_set]
        return self._build_partial(ordered)

    def partial_for_results(
        self, results: List[Result]
    ) -> Optional[Dict[str, Any]]:
        result_persons = {r.person for r in results if r.person}
        ordered = [p for p in self.persons if p in result_persons]
        return self._build_partial(ordered)
```

- [ ] **Step 4: Run all tests in the file**

```
uv run pytest tests/test_race_partial.py -vv
```

Expected: all tests PASSED (7 from Task 1 + 19 new = 26 total)

- [ ] **Step 5: Commit**

```
git add tests/test_race_partial.py sportorg/models/memory.py
git commit -m "refactor(report): add partial_for_* methods to Race"
```

---

## Task 3: Update `report_dialog.py`, delete `to_dict_partial`

**Files:**
- Modify: `sportorg/gui/dialogs/report_dialog.py` (lines 138–211, `apply_changes_impl`)
- Modify: `sportorg/models/memory.py` (delete `to_dict_partial`, ~lines 1737–1805 in current state after previous tasks)

**Interfaces:**
- Consumes: `Race.partial_for_persons`, `partial_for_results`, `partial_for_groups`, `partial_for_courses`, `partial_for_orgs` (all defined in Task 2)

- [ ] **Step 1: Replace the `_settings["selected"]` block in `report_dialog.py`**

Replace the entire block from `if _settings["selected"]:` through the closing `else:` (lines 139–211) with:

```python
        races_dict = []
        if _settings["selected"]:
            if mw.current_tab == 0:
                person_list = [obj.persons[i] for i in mw.get_selected_rows()]
                races_dict = [r.partial_for_persons(person_list) for r in races()]
            elif mw.current_tab == 1:
                result_list = [obj.results[i] for i in mw.get_selected_rows()]
                races_dict = [r.partial_for_results(result_list) for r in races()]
            elif mw.current_tab == 2:
                group_list = [obj.groups[i] for i in mw.get_selected_rows()]
                races_dict = [r.partial_for_groups(group_list) for r in races()]
            elif mw.current_tab == 3:
                course_list = [obj.courses[i] for i in mw.get_selected_rows()]
                races_dict = [r.partial_for_courses(course_list) for r in races()]
            elif mw.current_tab == 4:
                orgs_list = [obj.organizations[i] for i in mw.get_selected_rows()]
                races_dict = [r.partial_for_orgs(orgs_list) for r in races()]
        else:
            races_dict = [r.to_dict() for r in races()]
```

- [ ] **Step 2: Delete `to_dict_partial` from `memory.py`**

Remove the entire method — from the line `    def to_dict_partial(` through the line `        return None` that closes it (the `return None` immediately before `    def update_data`). The exact text to delete:

```python
    def to_dict_partial(
        self,
        person_list=None,
        group_list=None,
        course_list=None,
        orgs_list=None,
        result_list=None,
    ):
        if course_list and len(course_list) > 0:
            for group in self.groups:
                if group.course and group.course in course_list:
                    group_list.append(group.name)

        if group_list and len(group_list) > 0:
            for person in self.persons:
                if (
                    person.group
                    and person.group.name in group_list
                    and person not in person_list
                ):
                    person_list.append(person)

        if orgs_list and len(orgs_list) > 0:
            person_list = []
            for person in self.persons:
                if (
                    person.organization
                    and person.organization in orgs_list
                    and person not in person_list
                ):
                    person_list.append(person)

        if result_list and len(result_list) > 0:
            person_list = []
            for result in result_list:
                if result.person and result.person not in person_list:
                    person_list.append(result.person)

        if person_list and len(person_list) > 0:
            return_results = list()
            person_set = set(person_list)
            person_groups = set()
            person_orgs = set()
            for person in person_list:
                if person.group:
                    person_groups.add(person.group)
                if person.organization:
                    person_orgs.add(person.organization)
            # Preserve self.groups / self.courses / self.organizations order
            return_groups = [g for g in self.groups if g in person_groups]
            group_courses = {g.course for g in return_groups if g.course}
            return_courses = [c for c in self.courses if c in group_courses]
            return_orgs = [o for o in self.organizations if o in person_orgs]
            for result in self.results:
                if result.person in person_set:
                    return_results.append(result)

            return {
                "object": self.__class__.__name__,
                "id": str(self.id),
                "data": self.data.to_dict(),
                "settings": self.settings.copy(),
                "organizations": [item.to_dict() for item in return_orgs],
                "courses": [item.to_dict() for item in return_courses],
                "groups": [item.to_dict() for item in return_groups],
                "results": [item.to_dict() for item in return_results],
                "persons": [item.to_dict() for item in person_list],
            }
        return None

```

After deletion, `def update_data(self, dict_obj):` should immediately follow `def partial_for_results`.

- [ ] **Step 3: Verify no remaining references to `to_dict_partial`**

```powershell
Select-String -Recurse -Path "sportorg\","tests\" -Pattern "to_dict_partial"
```

Expected: no output (zero matches)

- [ ] **Step 4: Run the full test suite**

```
uv run poe test
```

Expected: all tests pass, coverage ≥ 42% branch threshold

- [ ] **Step 5: Run lint**

```
uv run poe lint
```

Expected: no errors

- [ ] **Step 6: Commit**

```
git add sportorg/models/memory.py sportorg/gui/dialogs/report_dialog.py
git commit -m "refactor(report): replace to_dict_partial with partial_for_* methods"
```
