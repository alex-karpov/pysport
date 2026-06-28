# Team Extracts Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, print-ready SportOrg report template that prints per-team athlete extracts grouped by age group, with columns for the admission committee.

**Architecture:** A single self-contained HTML report template at `docs/templates/reports/2_выписки_по_командам_регистрация.html`. Jinja embeds the race as JSON (`{{ race | tojson }}`); all logic and A4 pagination run in inline vanilla client-side JS. No `{% extends %}`, no external libraries — the rendered output is one standalone HTML file. A temporary Python preview script and a pytest render-smoke test support development.

**Tech Stack:** Jinja2 (SportOrg's `get_text_from_file`), vanilla JS (DOM API), CSS print (`@page`, fixed-size `.page` boxes), Python 3.8 / pytest / uv.

**Spec:** `docs/superpowers/specs/2026-06-28-team-extracts-design.md` (on branch `openspec-base`). The plan below is self-contained; consult the spec only for rationale.

## Global Constraints

- **Standalone output:** one HTML file, no external dependencies (no CDN/library). Race data embedded as JSON; CSS and JS inline.
- **Do NOT modify** `docs/templates/base_v2.html`, `docs/templates/style_v2.css.html`, `docs/templates/script_v2.js.html` — read-only. The template must NOT depend on them.
- **Python target 3.8**; type hints on all functions (mypy strict). Run everything via `uv run`.
- **Load race files via SportOrg's deserializer** (`sportorg.modules.backup.json.get_races_from_file`), never raw `json.load`.
- **Pagination = Variant 1** (fixed row height, arithmetic — no DOM measurement).
- **Print:** A4 portrait, 5mm margins all sides. Page header (team left / competition right) and column header repeat on every page. Grid fills the whole page even with few athletes. On a page break inside a group, keep ≥3 athletes together.
- **Fonts:** body 10pt sans-serif; column header 8pt; column «№» 8pt; column «Примечание» normal 10pt; «Допуск» monospace. (Source Excel was Arial 14pt printed at 70 % → ×0.7 rounded: 14→10pt, 12→8pt. Font families stay as-is — "Arial" was only a size reference.)
- **Row height:** 6mm — reference value measured from the Excel printout; `ROW_H` (JS) and the CSS row height must both equal 6mm.
- **Temporary files** (`team_extract_preview.py`, `tests/test_team_extract_report.py`) are committable; the author deletes them later.
- **Work happens in a git worktree:** `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-entry-template`, branch `ank/entry-template`, base `ank/dev`.

---

## File Structure

- Create: `docs/templates/reports/2_выписки_по_командам_регистрация.html` — the report template (Jinja + inline `<style>` + inline `<script>`). Single responsibility: render the team-extracts report from an embedded race.
- Create: `team_extract_preview.py` (repo root, temporary) — shared `load_sample_race()` + `render_report()`, plus a `__main__` that writes `team_extract_preview.html` and opens it in a browser.
- Create: `tests/test_team_extract_report.py` (temporary) — pytest render-smoke + structural-token checks.

The template's `<script>` is organized with anchor comments established in Task 1:
`// [helpers]`, `// [transforms]`, `// [data]`, `// [render]`, `// [pagination]`, `// [selftest]`, `// [main]`.
The `<style>` uses anchors `/* [base-css] */` and `/* [page-css] */`.

---

### Task 0: Create the worktree

**Files:** none (git only).

- [ ] **Step 1: Ensure base branch exists and create the worktree**

Run (Git Bash):
```bash
cd "C:/Users/ank/Documents/Prog/SportOrg/pysport"
git rev-parse --verify ank/dev            # must succeed; if not, create ank/dev first
git worktree add -b ank/entry-template \
  "C:/Users/ank/Documents/Prog/SportOrg/worktree/pysport-entry-template" ank/dev
```
Expected: `Preparing worktree (new branch 'ank/entry-template')` and the directory is created.

- [ ] **Step 2: Sync the environment in the worktree**

Run:
```bash
cd "C:/Users/ank/Documents/Prog/SportOrg/worktree/pysport-entry-template"
uv sync --frozen
```
Expected: environment resolves; no errors.

> All subsequent paths are relative to the worktree root, and all commands run there.

---

### Task 1: Render harness + smoke test + minimal template

**Files:**
- Create: `team_extract_preview.py`
- Create: `tests/test_team_extract_report.py`
- Create: `docs/templates/reports/2_выписки_по_командам_регистрация.html`

**Interfaces:**
- Produces: `team_extract_preview.load_sample_race() -> dict` (race dict via SportOrg deserializer); `team_extract_preview.render_report(race: dict) -> str` (rendered HTML).

- [ ] **Step 1: Write the preview/render harness**

Create `team_extract_preview.py`:
```python
"""TEMPORARY dev tool: render the team-extracts report from a SportOrg race file.

Delete together with tests/test_team_extract_report.py when the template is done.
"""
from __future__ import annotations

import os
import webbrowser
from typing import Any, Dict

from sportorg import config
from sportorg import settings as sportorg_settings
from sportorg.common.template import get_text_from_file
from sportorg.models.memory import Race, new_event, races, set_current_race_index
from sportorg.modules.backup.json import get_races_from_file

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "docs", "templates")
TEMPLATE_REL = "reports/2_выписки_по_командам_регистрация.html"
SAMPLE_RACE = os.path.join(REPO_ROOT, "data", "2024-01-28_relay_international.json")


def load_sample_race(path: str = SAMPLE_RACE) -> Dict[str, Any]:
    """Load a SportOrg race file via the official deserializer; return its dict."""
    new_event([Race()])
    with open(path, encoding="utf-8") as f:
        event, current = get_races_from_file(f)
    new_event(event)
    set_current_race_index(current)
    return races()[current].to_dict()


def render_report(race: Dict[str, Any]) -> str:
    """Render the report template with the same context the report dialog uses."""
    sportorg_settings.SETTINGS.templates_path = TEMPLATES_DIR
    return get_text_from_file(
        TEMPLATE_REL,
        race=race,
        races=[race],
        current_race=0,
        rent_cards=[],
        selected={"persons": []},
        name=config.NAME,
        version=str(config.VERSION),
    )


def main() -> None:
    race = load_sample_race()
    html = render_report(race)
    out = os.path.join(REPO_ROOT, "team_extract_preview.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote", out)
    webbrowser.open("file:///" + out.replace("\\", "/") + "?selftest")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing smoke test**

Create `tests/test_team_extract_report.py`:
```python
"""TEMPORARY: render-smoke + structural checks for the team-extracts template."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from team_extract_preview import load_sample_race, render_report  # noqa: E402


def test_renders_without_error():
    html = render_report(load_sample_race())
    assert "<table" in html
    assert "var race" in html
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
uv run pytest tests/test_team_extract_report.py -q
```
Expected: FAIL — `TemplateNotFound` (the template file does not exist yet).

- [ ] **Step 4: Create the minimal template skeleton with anchors**

Create `docs/templates/reports/2_выписки_по_командам_регистрация.html`:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Выписки по командам</title>
<style>
/* [base-css] */
/* [page-css] */
</style>
</head>
<body>
<div id="report"></div>
{% raw %}
<script>
var race = {% endraw %}{{ race | tojson }}{% raw %};

// [helpers]
// [transforms]
// [data]
// [render]
// [pagination]
// [selftest]

// [main]
document.addEventListener('DOMContentLoaded', function () {
  var root = document.getElementById('report');
  var table = document.createElement('table');
  table.appendChild(document.createElement('tbody'));
  root.appendChild(table);
});
</script>
{% endraw %}
</body>
</html>
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/test_team_extract_report.py -q
```
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add team_extract_preview.py tests/test_team_extract_report.py "docs/templates/reports/2_выписки_по_командам_регистрация.html"
git commit -m "feat(report): scaffold team extracts template and render harness"
```

---

### Task 2: Pure transforms + helpers + browser self-test

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_регистрация.html` (`<script>` anchors `// [helpers]`, `// [transforms]`, `// [selftest]`)
- Modify: `tests/test_team_extract_report.py`

**Interfaces:**
- Produces (JS): `formatZabeg(startGroup:int) -> string`, `formatDopusk(nationalCode:int) -> string`, `buildChipCounts(persons:[]) -> {number:count}`, `racePreparation(race)`, `Qualification{}`, `getById(list,id)`, `runSelfTest()`.

- [ ] **Step 1: Add helpers (after `// [helpers]`)**

```javascript
var Qualification = {'':'',0:'',3:'IIIю',2:'IIю',1:'Iю',6:'III',5:'II',4:'I',7:'КМС',8:'МС',9:'МСМК'};

function getById(list, id) {
  if (id) { for (var i = 0; i < list.length; i++) { if (list[i].id === id) return list[i]; } }
  return null;
}

function racePreparation(r) {
  for (var i = 0; i < r.persons.length; i++) {
    var p = r.persons[i];
    p.organization = getById(r.organizations, p.organization_id);
    p.group = getById(r.groups, p.group_id);
  }
  return r;
}

function buildChipCounts(persons) {
  var c = {};
  for (var i = 0; i < persons.length; i++) {
    var n = persons[i].card_number | 0;
    if (n > 0) c[n] = (c[n] || 0) + 1;
  }
  return c;
}
```

- [ ] **Step 2: Add the self-test vectors FIRST (after `// [selftest]`) — these define expected behavior**

```javascript
function runSelfTest() {
  var cases = [
    ['zabeg', 0, ''], ['zabeg', 1, '1'], ['zabeg', 9, '9'], ['zabeg', 10, ''],
    ['zabeg', 11, 'роз'], ['zabeg', 12, ''], ['zabeg', 13, 'кр'],
    ['zabeg', 91, '×'], ['zabeg', 99, '×'], ['zabeg', 100, ''],
    ['dopusk', 0, ''], ['dopusk', 11111, ' М П С Р Д'], ['dopusk', 1010, '   П   Р  '],
    ['dopusk', 101, '     С   Д'], ['dopusk', 11211, ''], ['dopusk', 111111, '']
  ];
  var fails = [];
  for (var i = 0; i < cases.length; i++) {
    var kind = cases[i][0], input = cases[i][1], want = cases[i][2];
    var got = kind === 'zabeg' ? formatZabeg(input) : formatDopusk(input);
    if (got !== want) fails.push(kind + '(' + input + ')=' + JSON.stringify(got) + ' want ' + JSON.stringify(want));
  }
  var banner = document.createElement('div');
  banner.className = 'selftest-banner';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:6px;z-index:9999;font-family:monospace;'
    + (fails.length ? 'background:#fbb;color:#900;' : 'background:#bfb;color:#060;');
  banner.textContent = fails.length ? ('SELFTEST FAIL: ' + fails.join(' | ')) : 'SELFTEST OK';
  document.body.appendChild(banner);
  if (fails.length) console.error(fails); else console.log('SELFTEST OK');
}
```

- [ ] **Step 3: Wire the self-test into `// [main]` (replace the placeholder body)**

Replace the `document.addEventListener('DOMContentLoaded', ...)` block from Task 1 with:
```javascript
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('selftest') >= 0) runSelfTest();
});
```

- [ ] **Step 4: Verify the self-test FAILS in the browser (transforms not implemented yet)**

Run:
```bash
uv run python team_extract_preview.py
```
Expected: browser opens; top banner is **red** `SELFTEST FAIL: ...` (because `formatZabeg`/`formatDopusk` are undefined — console shows ReferenceError). This is the red state.

- [ ] **Step 5: Implement the transforms (after `// [transforms]`)**

```javascript
function formatZabeg(sg) {
  sg = sg | 0;
  if (sg >= 1 && sg <= 9) return String(sg);
  if (sg === 11) return 'роз';
  if (sg === 13) return 'кр';
  if (sg >= 91 && sg <= 99) return '×';
  return '';
}

var DOPUSK_LETTERS = ['М', 'П', 'С', 'Р', 'Д']; // 10000, 1000, 100, 10, 1
function formatDopusk(code) {
  code = code | 0;
  if (code === 0) return '';
  var s = String(code);
  if (s.length > 5) return '';
  while (s.length < 5) s = '0' + s;
  for (var i = 0; i < 5; i++) { if (s[i] !== '0' && s[i] !== '1') return ''; }
  var out = '';
  for (var j = 0; j < 5; j++) { out += ' ' + (s[j] === '1' ? DOPUSK_LETTERS[j] : ' '); }
  return out;
}
```

- [ ] **Step 6: Verify the self-test PASSES in the browser**

Run:
```bash
uv run python team_extract_preview.py
```
Expected: top banner is **green** `SELFTEST OK`; console prints `SELFTEST OK`.

- [ ] **Step 7: Extend the pytest with token checks for the transforms**

Append to `tests/test_team_extract_report.py`:
```python
def test_contains_transforms_and_selftest():
    html = render_report(load_sample_race())
    assert "function formatZabeg" in html
    assert "function formatDopusk" in html
    assert "runSelfTest" in html
```

- [ ] **Step 8: Run the tests**

Run:
```bash
uv run pytest tests/test_team_extract_report.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 9: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_регистрация.html" tests/test_team_extract_report.py
git commit -m "feat(report): add zabeg/dopusk transforms with browser self-test"
```

---

### Task 3: Data model — grouping, ordering, numbering

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_регистрация.html` (`// [data]`)

**Interfaces:**
- Consumes: `formatZabeg`, `formatDopusk`, `Qualification`, `buildChipCounts`.
- Produces (JS): `fioOf(p)`, `fioSortKey(p)`, `buildTeamSlots(team, race) -> slot[]` where a slot is `{type:'data', groupId, groupName, person, index}` or `{type:'empty', separator?:true}`.

- [ ] **Step 1: Add the data-model functions (after `// [data]`)**

```javascript
function fioOf(p) {
  var parts = [];
  if (p.surname) parts.push(p.surname);
  if (p.name) parts.push(p.name);
  if (p.middle_name) parts.push(p.middle_name);
  return parts.join(' ');
}

function fioSortKey(p) {
  return [(p.surname || ''), (p.name || ''), (p.middle_name || '')].join(' ').toLowerCase();
}

// Build a flat list of row "slots" for one team:
// groups in race.groups order, athletes sorted by FIO, numbering restarts per group,
// one separator slot between groups, ungrouped athletes as a trailing block (empty group).
function buildTeamSlots(team, r) {
  var members = r.persons.filter(function (p) {
    return p.organization && p.organization.id === team.id;
  });
  var slots = [];

  function pushGroup(groupName, groupId, list) {
    list.sort(function (a, b) {
      var ka = fioSortKey(a), kb = fioSortKey(b);
      return ka < kb ? -1 : (ka > kb ? 1 : 0);
    });
    if (slots.length) slots.push({ type: 'empty', separator: true });
    for (var i = 0; i < list.length; i++) {
      slots.push({
        type: 'data',
        groupId: groupId || '__none__',
        groupName: groupName,
        person: list[i],
        index: i + 1
      });
    }
  }

  for (var gi = 0; gi < r.groups.length; gi++) {
    var g = r.groups[gi];
    var inGroup = members.filter(function (p) { return p.group && p.group.id === g.id; });
    if (inGroup.length) pushGroup(g.name, g.id, inGroup);
  }

  var ungrouped = members.filter(function (p) { return !p.group; });
  if (ungrouped.length) pushGroup('', null, ungrouped);

  return slots;
}
```

- [ ] **Step 2: Temporarily dump slot counts to verify grouping (in `// [main]`)**

Replace the `DOMContentLoaded` body with a temporary diagnostic:
```javascript
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('selftest') >= 0) runSelfTest();
  racePreparation(race);
  var lines = [];
  for (var i = 0; i < race.organizations.length; i++) {
    var t = race.organizations[i];
    var slots = buildTeamSlots(t, race);
    if (slots.length) lines.push(t.name + ': ' + slots.length + ' slots');
  }
  var pre = document.createElement('pre');
  pre.textContent = lines.join('\n');
  document.getElementById('report').appendChild(pre);
});
```

- [ ] **Step 3: Verify in the browser**

Run:
```bash
uv run python team_extract_preview.py
```
Expected: the page lists each non-empty team with a slot count (data rows + separators). Sanity-check a couple of teams against the persons tab if desired. No JS errors in console.

- [ ] **Step 4: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_регистрация.html"
git commit -m "feat(report): build per-team grouped/sorted row slots"
```

---

### Task 4: Table rendering + base CSS

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_регистрация.html` (`// [render]`, `/* [base-css] */`)
- Modify: `tests/test_team_extract_report.py`

**Interfaces:**
- Consumes: `buildTeamSlots`, `fioOf`, `formatZabeg`, `formatDopusk`, `Qualification`.
- Produces (JS): `COLS` (column config), `cellValues(slot, chipCounts) -> {key:string,...,_chipDup:bool}`, `buildTable(rows, chipCounts) -> <table>`.

- [ ] **Step 1: Add column config + cell values + table builder (after `// [render]`)**

```javascript
var COLS = [
  { key: 'index',  title: '№',                     width: '2.4',  align: 'right',  cls: 'c-index' },
  { key: 'fio',    title: 'Фамилия, имя, отчество', width: '34.3', align: 'left',   cls: 'c-fio' },
  { key: 'zabeg',  title: 'Забег',                  width: '3.9',  align: 'center', cls: 'c-zabeg' },
  { key: 'birth',  title: 'Дата рождения',          width: '10.8', align: 'center', cls: 'c-birth' },
  { key: 'group',  title: 'Группа',                 width: '4.5',  align: 'center', cls: 'c-group' },
  { key: 'qual',   title: 'Квал',                   width: '4.9',  align: 'center', cls: 'c-qual' },
  { key: 'chip',   title: 'Чип',                    width: '9.4',  align: 'center', cls: 'c-chip' },
  { key: 'dopusk', title: 'Допуск',                 width: '13.1', align: 'left',   cls: 'c-dopusk' },
  { key: 'note',   title: 'Примечание',             width: '',     align: 'left',   cls: 'c-note' }
];

function cellValues(slot, chipCounts) {
  if (slot.type !== 'data') return null;
  var p = slot.person;
  var card = p.card_number | 0;
  return {
    index: String(slot.index),
    fio: fioOf(p),
    zabeg: formatZabeg(p.start_group),
    birth: p.birthday || '',
    group: slot.groupName || '',
    qual: Qualification[p.qual] || '',
    chip: card > 0 ? String(card) : '',
    dopusk: formatDopusk(p.national_code),
    note: p.comment || '',
    _chipDup: card > 0 && chipCounts[card] > 1
  };
}

function buildTable(rows, chipCounts) {
  var table = document.createElement('table');
  table.className = 'extract';

  var colgroup = document.createElement('colgroup');
  COLS.forEach(function (c) {
    var col = document.createElement('col');
    if (c.width !== '') col.style.width = c.width + '%';
    colgroup.appendChild(col);
  });
  table.appendChild(colgroup);

  var thead = document.createElement('thead');
  var htr = document.createElement('tr');
  COLS.forEach(function (c) {
    var th = document.createElement('th');
    th.textContent = c.title;
    th.className = c.cls + ' a-' + c.align;
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  table.appendChild(thead);

  var tbody = document.createElement('tbody');
  rows.forEach(function (slot) {
    var tr = document.createElement('tr');
    tr.className = slot.type === 'data' ? 'row-data' : 'row-empty';
    var vals = cellValues(slot, chipCounts);
    COLS.forEach(function (c) {
      var td = document.createElement('td');
      td.className = c.cls + ' a-' + c.align;
      if (vals) {
        td.textContent = vals[c.key] || '';
        if (c.key === 'chip' && vals._chipDup) td.className += ' chip-dup';
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}
```

- [ ] **Step 2: Render one full team (temporary, in `// [main]`)**

Replace the `DOMContentLoaded` body with:
```javascript
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('selftest') >= 0) runSelfTest();
  racePreparation(race);
  var chipCounts = buildChipCounts(race.persons);
  var root = document.getElementById('report');
  for (var i = 0; i < race.organizations.length; i++) {
    var slots = buildTeamSlots(race.organizations[i], race);
    if (!slots.length) continue;
    root.appendChild(buildTable(slots, chipCounts));
  }
});
```

- [ ] **Step 3: Add base CSS (after `/* [base-css] */`)**

```css
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; margin: 0; }

table.extract {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-family: Arial, "DejaVu Sans", sans-serif;
  font-size: 10pt;
}
table.extract th, table.extract td {
  border: 0.5px dashed #999;
  padding: 0 4px;
  height: 6mm;               /* fixed row height (measured ref) — keep in sync with ROW_H in JS */
  overflow: hidden;
  white-space: nowrap;
  vertical-align: bottom;    /* spec: cells bottom-aligned */
}
table.extract th:first-child, table.extract td:first-child { border-left: 1px solid #000; }
table.extract th:last-child,  table.extract td:last-child  { border-right: 1px solid #000; }

table.extract thead th { font-size: 8pt; border: 1px solid #000; background: #ddd; vertical-align: middle; }

.a-left   { text-align: left; }
.a-center { text-align: center; }
.a-right  { text-align: right; }

.c-index { font-size: 8pt; }                      /* spec: № is 8pt; Примечание stays normal 10pt */
table.extract .c-dopusk { font-family: "Courier New", monospace; white-space: pre; vertical-align: middle; }  /* qualified to beat `table.extract td` specificity */

td.chip-dup { background: #cfcfcf; font-style: italic; }
```

- [ ] **Step 4: Verify in the browser**

Run:
```bash
uv run python team_extract_preview.py
```
Expected (no pagination yet — one long table per team):
- Columns appear in the spec order with the right widths; «Допуск» monospace; «№» visibly smaller (8pt); «Примечание» normal (10pt).
- Alignments: № right; ФИО/Допуск/Примечание left; others centered.
- Empty separator rows appear between age groups; numbering restarts each group.
- Any duplicated chip number is shown on a grey, italic cell.
- Self-test banner still green.

- [ ] **Step 5: Extend the pytest with structural-token checks**

Append to `tests/test_team_extract_report.py`:
```python
def test_contains_column_headers():
    html = render_report(load_sample_race())
    for label in ["Фамилия, имя, отчество", "Забег", "Дата рождения",
                  "Группа", "Квал", "Чип", "Допуск", "Примечание"]:
        assert label in html
    assert "table-layout: fixed" in html
    assert "chip-dup" in html


def test_first_org_name_present():
    race = load_sample_race()
    orgs = [o for o in race["organizations"] if o.get("name")]
    assert orgs, "sample race has no named organizations"
    assert orgs[0]["name"] in render_report(race)
```

- [ ] **Step 6: Run the tests**

Run:
```bash
uv run pytest tests/test_team_extract_report.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_регистрация.html" tests/test_team_extract_report.py
git commit -m "feat(report): render extract table with columns, styling, chip duplicates"
```

---

### Task 5: Pagination (Variant 1) + page CSS

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_регистрация.html` (`// [pagination]`, `// [main]`, `/* [page-css] */`)

**Interfaces:**
- Consumes: `buildTeamSlots`, `buildTable`, `buildChipCounts`, `racePreparation`, `race.data.short_title`.
- Produces (JS): `ROWS_PER_PAGE`, `applyKeepMin(rows, start, take) -> int`, `paginate(slots) -> slot[][]`, `buildPage(team, rowSlice, chipCounts) -> <div.page>`.

- [ ] **Step 1: Add the pagination logic (after `// [pagination]`)**

```javascript
var PAGE_H = 287, HEADER_H = 7, THEAD_H = 6, ROW_H = 6;   // mm; ROW_H must match CSS row height (6mm measured ref)
// SAFETY_MM reserves space for inter-row borders (~0.5px × rows) the nominal mm model omits,
// so the last real row never overflows the page. Lower it for denser pages.
var SAFETY_MM = 12;
var ROWS_PER_PAGE = Math.max(1, Math.floor((PAGE_H - HEADER_H - THEAD_H - SAFETY_MM) / ROW_H));
var KEEP_MIN = 3;   // keep at least this many of a group together on a page split

// If a page break falls inside one group leaving < KEEP_MIN rows on either side,
// pull the break back to the start of that group's run on this page.
function applyKeepMin(rows, start, take) {
  var end = start + take;
  if (end >= rows.length) return take;
  var prev = rows[end - 1], next = rows[end];
  if (!(prev && next && prev.type === 'data' && next.type === 'data' && prev.groupId === next.groupId)) {
    return take;
  }
  var gid = next.groupId, j;
  var placed = 0;
  for (j = end - 1; j >= start; j--) { if (rows[j].type === 'data' && rows[j].groupId === gid) placed++; else break; }
  var rest = 0;
  for (j = end; j < rows.length; j++) { if (rows[j].type === 'data' && rows[j].groupId === gid) rest++; else break; }
  if (placed >= KEEP_MIN && rest >= KEEP_MIN) return take;
  var firstIdx = end - 1;
  while (firstIdx > start && rows[firstIdx - 1].type === 'data' && rows[firstIdx - 1].groupId === gid) firstIdx--;
  var newTake = firstIdx - start;
  return newTake >= 1 ? newTake : take;   // group larger than a page: allow split to guarantee progress
}

// Split a team's slots into page-sized row slices (Variant 1: fixed row height).
function paginate(slots) {
  var pages = [];
  var i = 0;
  while (i < slots.length) {
    while (i < slots.length && slots[i].separator) i++;   // drop separators at page top
    if (i >= slots.length) break;
    var take = Math.min(ROWS_PER_PAGE, slots.length - i);
    take = applyKeepMin(slots, i, take);
    var slice = slots.slice(i, i + take);
    while (slice.length && slice[slice.length - 1].separator) slice.pop();   // no trailing separator
    while (slice.length < ROWS_PER_PAGE) slice.push({ type: 'empty' });      // fill to bottom
    pages.push(slice);
    i += take;
  }
  return pages;
}

function buildPage(team, rowSlice, chipCounts) {
  var page = document.createElement('div');
  page.className = 'page';

  var header = document.createElement('div');
  header.className = 'page-header';
  var left = document.createElement('span');
  left.textContent = team.name || '';
  var right = document.createElement('span');
  right.textContent = (race.data && race.data.short_title) || '';
  header.appendChild(left);
  header.appendChild(right);
  page.appendChild(header);

  page.appendChild(buildTable(rowSlice, chipCounts));
  return page;
}
```

- [ ] **Step 2: Replace `// [main]` body with the final renderer**

```javascript
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('selftest') >= 0) runSelfTest();
  racePreparation(race);
  var chipCounts = buildChipCounts(race.persons);
  var root = document.getElementById('report');
  root.innerHTML = '';
  for (var oi = 0; oi < race.organizations.length; oi++) {
    var team = race.organizations[oi];
    var slots = buildTeamSlots(team, race);
    if (!slots.length) continue;
    var pages = paginate(slots);
    for (var pi = 0; pi < pages.length; pi++) {
      root.appendChild(buildPage(team, pages[pi], chipCounts));
    }
  }
});
```

- [ ] **Step 3: Add page CSS (after `/* [page-css] */`)**

```css
@page { size: A4 portrait; margin: 5mm; }

.page {
  box-sizing: border-box;
  width: 200mm;          /* 210 − 2×5 */
  height: 287mm;         /* 297 − 2×5 */
  overflow: hidden;
  page-break-after: always;
  display: flex;
  flex-direction: column;
}
.page:last-child { page-break-after: auto; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  font-family: Arial, "DejaVu Sans", sans-serif;
  font-size: 10pt;
  font-weight: bold;
  height: 7mm;           /* must match HEADER_H */
}

.page table.extract { flex: 1 1 auto; height: 100%; }   /* fill to bottom: stretch rows to the page edge */

@media screen {
  .page { border: 1px solid #ccc; margin: 4mm auto; background: #fff; }
}
@media print {
  .selftest-banner { display: none !important; }
}
```

- [ ] **Step 4: Verify pagination on screen**

Run:
```bash
uv run python team_extract_preview.py
```
Expected:
- Each `.page` is a visible A4 box; each team starts on its own page; the page header (team left / competition right) and the column header appear at the top of every page.
- Pages are filled with blank ruled rows down to the bottom even when a team has few athletes.
- Separators do not appear at the very top of a page.

- [ ] **Step 5: Verify pagination in print preview**

In the opened browser, press `Ctrl+P` and check the print preview:
- One team per page boundary; header + column header repeat on every printed sheet.
- The grid fills each sheet to the bottom; no stray extra blank pages.
- Where a group spills across a page break, at least three of its athletes stay together (no 1–2-row orphan). To exercise this, temporarily lower `SAFETY_MM`/`ROWS_PER_PAGE` (e.g., so ~6 rows/page) and re-run; confirm keep-≥3 holds; then restore.
- Self-test banner is hidden in print.

- [ ] **Step 6: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_регистрация.html"
git commit -m "feat(report): paginate to A4 pages with repeated headers, fill, keep-3"
```

---

### Task 6: Final verification, row-height tuning, deployment note

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_регистрация.html` (tune constants only)
- Modify: `tests/test_team_extract_report.py` (final assertions)

- [ ] **Step 1: Tune the fixed row height so a page fills exactly**

`ROW_H` = CSS row `height` = **6mm** is the measured reference from the Excel printout — keep it. In print preview, count rows on a full page; if the last data/blank row is clipped or a large gap remains, adjust `HEADER_H`/`THEAD_H` (the page-header and column-header heights) — NOT `ROW_H` — until a full page shows no clipping and minimal bottom gap (the `flex: 1` on the table absorbs sub-row residue). If you must change the row height, change **both** the CSS `height: 6mm` and the JS `ROW_H` to the same value.

Run after each change:
```bash
uv run python team_extract_preview.py
```
Expected: a full team page shows a complete, unclipped grid reaching the bottom.

- [ ] **Step 2: Finalize the pytest (full structural coverage)**

Ensure `tests/test_team_extract_report.py` contains these (add any missing):
```python
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
```

- [ ] **Step 3: Run the full template test suite**

Run:
```bash
uv run pytest tests/test_team_extract_report.py -q
```
Expected: PASS (all tests green).

- [ ] **Step 4: Run format + lint to keep the repo clean**

Run:
```bash
uv run poe format
uv run poe lint
```
Expected: no errors (the preview script and test are formatted/linted).

- [ ] **Step 5: Manual acceptance checklist (browser)**

Run `uv run python team_extract_preview.py` and confirm against the spec:
- [ ] Header: team name left, `short_title` right, bold 10pt, on every page.
- [ ] Column order/widths match the spec; «Допуск» monospace; «№» 8pt, «Примечание» normal 10pt; header row 8pt.
- [ ] Alignments: № right; ФИО/Допуск/Примечание left; others center; cells bottom-aligned except «Допуск» (center).
- [ ] Groups in the Groups-tab order; athletes sorted by ФИО; numbering restarts per group; one blank row between groups.
- [ ] Ungrouped athletes form a trailing block with an empty «Группа» cell.
- [ ] Забег mapping and Допуск bitmask render per the spec examples (self-test green).
- [ ] Duplicated chip → grey italic cell.
- [ ] Pages fill to the bottom; each team starts on a new page; keep-≥3 on group splits.

- [ ] **Step 6: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_регистрация.html" tests/test_team_extract_report.py
git commit -m "test(report): finalize team extracts checks and tune row height"
```

- [ ] **Step 7: Deployment note (no code change)**

To use the report inside SportOrg: open Settings → set the templates folder to a directory containing this template under `reports/` (or copy `2_выписки_по_командам_регистрация.html` into `sportorg/data/templates/reports/`). It then appears in the «Создание протокола» dialog. The author handles the final relocation.

---

## Self-Review

**Spec coverage:**
- Header (team/short_title, bold 10pt, every page) → Task 5 (`buildPage`, page CSS).
- Columns + widths + alignments + per-column fonts → Task 4 (`COLS`, base CSS), Task 6 checklist.
- Grouping by group in `race.groups` order, FIO sort, per-group numbering, blank row between groups, ungrouped trailing block (empty Группа) → Task 3 (`buildTeamSlots`).
- Забег mapping → Task 2 (`formatZabeg`) + self-test.
- Допуск bitmask → Task 2 (`formatDopusk`) + self-test vectors.
- Chip duplicate (whole race) grey+italic → Task 3/4 (`buildChipCounts`, `cellValues`, `.chip-dup`).
- Pagination: A4 5mm, repeat header per page, fill to bottom, keep-≥3, page-per-team (Variant 1, fixed row height) → Task 5 (`paginate`, `applyKeepMin`, page CSS).
- Standalone, no base_v2 dependency, embedded race JSON → Task 1 skeleton + Task 6 `test_standalone_no_external_refs`.
- Load via SportOrg deserializer → Task 1 `load_sample_race`.

**Placeholder scan:** No TBD/TODO; every code step shows complete code; `ROW_H`/`ROWS_PER_PAGE` have concrete starting values with an explicit tuning step (Task 6). ✓

**Type/name consistency:** `formatZabeg`, `formatDopusk`, `buildChipCounts`, `racePreparation`, `buildTeamSlots`, `cellValues`, `buildTable`, `applyKeepMin`, `paginate`, `buildPage`, `ROWS_PER_PAGE`, `ROW_H` used consistently across tasks; slot shape (`type`/`groupId`/`groupName`/`person`/`index`/`separator`) consistent between Task 3 producer and Task 4/5 consumers. ✓

---

## Post-implementation refinements (after final review / visual verification)

Applied to the template after the tasks above; spec updated to match:

1. **Last-row clipping fix (Variant A).** The nominal mm model omitted inter-row borders
   (~0.5px × N ≈ 6mm), so the last row overflowed and was clipped by `overflow:hidden`.
   Added `SAFETY_MM` reserve to `ROWS_PER_PAGE` (43/page) and `table { height:100% }` to
   stretch rows to the page bottom.
2. **Примечание font** back to normal 10pt (only «№» stays 8pt).
3. **keep-≥2 → keep-≥3.** `applyKeep2` renamed `applyKeepMin` with `KEEP_MIN = 3`.
4. **«Без команды» block.** `buildTeamSlots` refactored to delegate to `buildSlots(members, r)`;
   a trailing block renders athletes with no organization so they are not silently dropped.
5. **Russian sort collation.** FIO comparator uses `localeCompare(…, 'ru')` (`ё` after `е`).
6. **Допуск monospace scoped to `td`** (`table.extract td.c-dopusk`) so the column header
   stays in the body font.
