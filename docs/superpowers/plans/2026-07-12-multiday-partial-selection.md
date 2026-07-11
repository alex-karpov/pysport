# Multi-day cross-day Send-Selected — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make "Send selected" in multi-day competitions show the selected athletes' results across **all** days (matched by `multi_day_id`) instead of returning `None` for non-active days and crashing the sum templates.

**Architecture:** Add one identity-independent resolver on `Race` — `partial_for_multi_day_ids(ids)` — that selects this day's persons by `multi_day_id` and reuses the existing `_build_partial`, never returning `None` (falls back to `_empty_partial()`). `report_dialog` branches on `len(races()) > 1`: single-day keeps the current per-tab exact path (preserving the 2026-07-11 results fix); multi-day reduces the current-day selection to a `set[str]` of `multi_day_id`s and calls the new resolver for every day.

**Tech Stack:** Python 3.13, pytest, PySide6 (GUI), poethepoet (`poe`), uv.

## Global Constraints

- All Python runs through uv on 3.13: `uv run --python 3.13 poe test`, `uv run --python 3.13 poe lint`. Never bare `python`.
- GUI deps require the extra: `uv sync --frozen --python 3.13 --extra gui` (needed for `report_dialog` import / lint).
- **Code changes happen in the worktree** `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-to-dict-partial-fix` (branch `ank/to-dict-partial`). This worktree already carries the uncommitted 2026-07-11 results fix in `sportorg/models/memory.py` and `tests/test_race_partial.py`; build on top of it.
- This plan document lives in the main repo on branch `openspec-multiday`; do **not** edit it from the worktree.
- Spec: `docs/superpowers/specs/2026-07-01-to-dict-partial-refactor-design.md`, addendum **2026-07-12** (invariants 7–9). Read it before starting.
- Commits only when the user explicitly asks. The commit steps below describe the intended commit; do not push, and do not force-push `ank/to-dict-partial` without explicit confirmation.

---

### Task 1: `Race.partial_for_multi_day_ids` + `_empty_partial` (model + unit tests)

**Files:**
- Modify: `sportorg/models/memory.py` — import line 9 (`from typing import ...`); add two methods after `partial_for_results` (currently ends ~line 1798).
- Test: `tests/test_race_partial.py` — append four tests after `test_partial_for_results_output_in_model_order`.

**Interfaces:**
- Consumes: existing `Race._build_partial(persons, results=None)`, `Race.data.to_dict()`, `Race.settings`, `Race.id`, `Person.multi_day_id` (`f"{full_name} {group.name}"` or bare `full_name`).
- Produces:
  - `Race._empty_partial(self) -> Dict[str, Any]` — valid dict, empty entity arrays.
  - `Race.partial_for_multi_day_ids(self, ids: Set[str]) -> Dict[str, Any]` — never `None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_race_partial.py` (imports `Group`, `Person`, `Race`, `ResultManual` already present):

```python
# --- partial_for_multi_day_ids ---


def test_partial_for_multi_day_ids_matches_selected_athlete(r: Race) -> None:
    p0, p1 = r.persons[0], r.persons[1]
    p0.surname, p0.name = "Ivanov", "Ivan"
    p1.surname, p1.name = "Petrov", "Petr"
    result = r.partial_for_multi_day_ids({p0.multi_day_id})
    assert result is not None
    assert [p["id"] for p in result["persons"]] == [str(p0.id)]
    assert [res["person_id"] for res in result["results"]] == [str(p0.id)]


def test_partial_for_multi_day_ids_no_match_returns_empty_valid_dict(r: Race) -> None:
    # A day where none of the selected athletes competed must return a valid,
    # non-None dict so the multi-day template's racePreparation() does not crash.
    result = r.partial_for_multi_day_ids({"Nobody Here M99"})
    assert result is not None
    assert result["persons"] == []
    assert result["results"] == []
    assert result["groups"] == []
    assert result["id"] == str(r.id)
    assert "data" in result
    assert "settings" in result


def test_partial_for_multi_day_ids_matches_across_race_objects() -> None:
    # The same athlete lives on two separate Race objects (two days). Selection
    # by multi_day_id must resolve on each day independently of object identity.
    def make_day() -> Race:
        day = Race()
        g = Group()
        g.name = "M21"
        day.groups.append(g)
        p = Person()
        p.surname, p.name = "Ivanov", "Ivan"
        p.group = g
        day.persons.append(p)
        res = ResultManual()
        res.person = p
        day.results.append(res)
        return day

    day1, day2 = make_day(), make_day()
    athlete_id = day1.persons[0].multi_day_id
    assert athlete_id == day2.persons[0].multi_day_id  # identical key across days

    r1 = day1.partial_for_multi_day_ids({athlete_id})
    r2 = day2.partial_for_multi_day_ids({athlete_id})
    assert [res["id"] for res in r1["results"]] == [str(day1.results[0].id)]
    assert [res["id"] for res in r2["results"]] == [str(day2.results[0].id)]


def test_partial_for_multi_day_ids_person_order_follows_model(r: Race) -> None:
    p0, p2 = r.persons[0], r.persons[2]
    p0.surname, p0.name = "Bbb", "B"
    p2.surname, p2.name = "Aaa", "A"
    result = r.partial_for_multi_day_ids({p0.multi_day_id, p2.multi_day_id})
    # Output order is self.persons order (p0 at index 0 before p2 at index 2),
    # not the set's arbitrary order.
    assert [p["id"] for p in result["persons"]] == [str(p0.id), str(p2.id)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/ank/Documents/Prog/SportOrg/worktree/pysport-to-dict-partial-fix && uv run --python 3.13 pytest tests/test_race_partial.py -k multi_day_ids -v`
Expected: FAIL — `AttributeError: 'Race' object has no attribute 'partial_for_multi_day_ids'`.

- [ ] **Step 3: Add `Set` to the typing import**

In `sportorg/models/memory.py` line 9:

```python
from typing import Any, Dict, List, Optional, Set
```

- [ ] **Step 4: Implement the two methods**

In `sportorg/models/memory.py`, immediately after `partial_for_results` (after its `return self._build_partial(ordered, results=results)` line):

```python
    def _empty_partial(self) -> Dict[str, Any]:
        # A structurally valid but empty partial. Used for multi-day days where
        # none of the selected athletes competed: returning None here would put a
        # null into `races` and crash templates that iterate every day
        # (racePreparation touches race.persons -> "race is null").
        return {
            "object": self.__class__.__name__,
            "id": str(self.id),
            "data": self.data.to_dict(),
            "settings": self.settings.copy(),
            "organizations": [],
            "courses": [],
            "groups": [],
            "results": [],
            "persons": [],
        }

    def partial_for_multi_day_ids(self, ids: Set[str]) -> Dict[str, Any]:
        # Identity-independent selection for multi-day events: each day is a
        # separate Race, so persons are matched by multi_day_id (name + group),
        # not by object identity. Never returns None.
        persons = [p for p in self.persons if p.multi_day_id in ids]
        return self._build_partial(persons) or self._empty_partial()
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `uv run --python 3.13 pytest tests/test_race_partial.py -k multi_day_ids -v`
Expected: 4 passed.

- [ ] **Step 6: Run the whole partial suite for regressions**

Run: `uv run --python 3.13 pytest tests/test_race_partial.py -v`
Expected: all pass (27 pre-existing + 4 new = 31), including the 2026-07-11 results-fix tests.

- [ ] **Step 7: Commit** (only if the user has asked to commit)

```bash
git add sportorg/models/memory.py tests/test_race_partial.py
git commit -m "feat(report): add Race.partial_for_multi_day_ids for cross-day selection"
```

---

### Task 2: `report_dialog` branches single-day vs multi-day

**Files:**
- Modify: `sportorg/gui/dialogs/report_dialog.py` — the `if _settings["selected"]:` block in `apply_changes_impl` (currently lines ~138–156).

**Interfaces:**
- Consumes: `Race.partial_for_multi_day_ids(ids)` (Task 1); existing `partial_for_persons/results/groups/courses/orgs`; `races()`, `race()`, `mw.get_selected_rows()`, `mw.current_tab`; `Person.multi_day_id`, `Person.group`, `Group.course.id`, `Person.organization`.
- Produces: `races_dict` — one dict per day (never `None` in the multi-day branch).

- [ ] **Step 1: Replace the selected-branch**

In `sportorg/gui/dialogs/report_dialog.py`, replace the whole block from `races_dict = []` down to (and including) the `else: races_dict = [r.to_dict() for r in races()]` with:

```python
        races_dict = []
        if _settings["selected"]:
            rows = mw.get_selected_rows()
            multiday = len(races()) > 1
            if mw.current_tab == 0:
                person_list = [obj.persons[i] for i in rows]
                if multiday:
                    ids = {p.multi_day_id for p in person_list}
                    races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
                else:
                    races_dict = [r.partial_for_persons(person_list) for r in races()]
            elif mw.current_tab == 1:
                result_list = [obj.results[i] for i in rows]
                if multiday:
                    ids = {
                        res.person.multi_day_id for res in result_list if res.person
                    }
                    races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
                else:
                    races_dict = [r.partial_for_results(result_list) for r in races()]
            elif mw.current_tab == 2:
                group_list = [obj.groups[i] for i in rows]
                if multiday:
                    group_set = set(group_list)
                    ids = {
                        p.multi_day_id for p in obj.persons if p.group in group_set
                    }
                    races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
                else:
                    races_dict = [r.partial_for_groups(group_list) for r in races()]
            elif mw.current_tab == 3:
                course_list = [obj.courses[i] for i in rows]
                if multiday:
                    course_ids = {c.id for c in course_list}
                    ids = {
                        p.multi_day_id
                        for p in obj.persons
                        if p.group
                        and p.group.course
                        and p.group.course.id in course_ids
                    }
                    races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
                else:
                    races_dict = [r.partial_for_courses(course_list) for r in races()]
            elif mw.current_tab == 4:
                orgs_list = [obj.organizations[i] for i in rows]
                if multiday:
                    orgs_set = set(orgs_list)
                    ids = {
                        p.multi_day_id
                        for p in obj.persons
                        if p.organization in orgs_set
                    }
                    races_dict = [r.partial_for_multi_day_ids(ids) for r in races()]
                else:
                    races_dict = [r.partial_for_orgs(orgs_list) for r in races()]
        else:
            races_dict = [r.to_dict() for r in races()]
```

Note: the single-day branches are byte-for-byte the current behavior (for one race, `[r.partial_for_X(list) for r in races()]` iterates exactly one element). Only the `multiday` branches are new.

- [ ] **Step 2: Lint**

Run: `cd /c/Users/ank/Documents/Prog/SportOrg/worktree/pysport-to-dict-partial-fix && uv run --python 3.13 poe lint`
Expected: clean. (If it fails with `No module named 'PySide6'`, run `uv sync --frozen --python 3.13 --extra gui` first, then re-run.)

- [ ] **Step 3: Full test suite (no regressions)**

Run: `uv run --python 3.13 poe test`
Expected: all pass, coverage ≥ threshold (previously 238 passed / 12 skipped; now +4 new tests).

- [ ] **Step 4: Manual verification against the reported case**

Using the user's files (`data\tmp\4_результаты_сумма_времени.html` template, a 3-day race):
1. Open the multi-day race, enable **Send selected**, template = сумма.
2. **Участники** tab: select athletes → generate. Expect: selected athletes shown with results from **all three days**; no `race is null` in the browser console.
3. **Результаты** tab: select rows → all three days shown for those athletes.
4. **Группы / Дистанции / Коллективы** tabs: select → all three days shown for the athletes resolved from the current day.
5. Confirm the browser console (F12) is clean — no `TypeError: ... race is null`.
6. Sanity: open a **single-day** race, Send selected on **Результаты**, and confirm exact-row behavior still holds (the 2026-07-11 fix) — selecting one result of an athlete who has two results in that race shows only the selected one.

- [ ] **Step 5: Commit** (only if the user has asked to commit)

```bash
git add sportorg/gui/dialogs/report_dialog.py
git commit -m "fix(report): cross-day selection for multi-day events (no null-day crash)"
```

---

## Self-Review

**Spec coverage:**
- Threshold `len(races()) > 1` → Task 2 Step 1 (`multiday = len(races()) > 1`). ✓
- Single-day path unchanged, invariant 6/9 preserved → Task 2 single-day branches identical to current; Task 1 Step 6 re-runs the results-fix tests. ✓
- `partial_for_multi_day_ids` never `None`, empty day valid (invariant 7) → Task 1 Step 4 + `test_..._no_match_returns_empty_valid_dict`. ✓
- Person order = `self.persons`, results all of matched persons this day (invariant 8) → `test_..._person_order_follows_model`, `test_..._matches_selected_athlete`. ✓
- Per-tab id resolution table (persons/results/groups/courses/orgs) → Task 2 Step 1 covers all five tabs. ✓
- Cross-day identity independence → `test_..._matches_across_race_objects`. ✓

**Placeholder scan:** none — all code shown in full, exact commands and expected output given.

**Type consistency:** `partial_for_multi_day_ids(ids: Set[str]) -> Dict[str, Any]` defined in Task 1, consumed with a `set` literal in Task 2 (all five tabs). `_empty_partial` returns the same key set as `_build_partial`. `Set` added to imports in Task 1 Step 3. ✓
