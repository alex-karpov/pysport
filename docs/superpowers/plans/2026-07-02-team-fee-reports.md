# Team Fee Reports (взнос) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two standalone, print-ready SportOrg report templates on top of the team-extracts report: per-person start fee + chip rental (variant 2, fixed ЧСФО/ПСФО) and a per-day variant (variant 3, ЧСФО/ПСФО charged per participation/non-participation day), each with a per-team fee summary under the table.

**Architecture:** Each report is a single self-contained HTML file cloned from `2_выписки_по_командам_регистрация.html` (Jinja embeds `{{ race | tojson }}`; all logic + A4 pagination in inline vanilla JS; no `{% extends %}`, no external libs). The two files are byte-identical except the `[fee-config]` `TARIFF` literal — the fee functions are pure and take explicit tariff entries, so the selftest is shared verbatim. Variant 3 is produced by copying variant 2 and swapping only `[fee-config]`.

**Tech Stack:** Jinja2 (SportOrg's `get_text_from_file`), vanilla JS (DOM API), CSS print (`@page`, fixed-size `.page` boxes), Python 3.8 / pytest / uv.

**Spec:** `docs/superpowers/specs/2026-07-02-team-fee-reports-design.md` (on branch `openspec-fee`). The plan below is self-contained; consult the spec only for rationale.

## Global Constraints

- **Standalone output:** each report is one HTML file, no external dependencies. Race data embedded as JSON; CSS and JS inline.
- **Two files differ only in `[fee-config]`** (the `TARIFF` literal). All other bytes identical. Variant 3 = copy of variant 2 with `[fee-config]` swapped.
- **Do NOT modify** `docs/templates/base_v2.html`, `docs/templates/style_v2.css.html`, `docs/templates/script_v2.js.html`, and do NOT touch the existing `2_выписки_по_командам_регистрация.html` (the fee reports are new files).
- **Python target 3.8**; type hints on all functions (mypy strict). Run everything via `uv run`.
- **Load race files via SportOrg's deserializer** (reuse `team_extract_preview.load_sample_race`), never raw `json.load`.
- **Fee config lives in one editable block** `// [fee-config]` at the top of the script, header comment «ПРАВЬ ЗДЕСЬ». Constants: `EVENT_DAYS=3`, `CHIP_PER_DAY=100`, `CHIP_PER_DAY_BK=150`, `CHIP_BK_MARK='бк'`, `TARIFF`.
- **Взнос column = start fee + chip rental** per person → the column sums to the team «Итого».
- **Summary is per-team** (no grand total), rendered as full-width rows at the end of the team's table; the block is not split across pages.
- **Pagination = Variant 1** (fixed row height 6mm) inherited unchanged from the extract template.
- **Temporary files** (`team_fee_preview.py`, `tests/test_team_fee_report.py`) are committable; the author deletes them later (as with the extract report).
- **Work happens in a git worktree:** `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-entry-fee`, branch `ank/entry-fee`, base `ank/entry-template` (so the finished extract template + preview harness + tests are present).

---

## File Structure

- Create: `docs/templates/reports/2_выписки_по_командам_взнос.html` — variant 2 report (clone of extract + fee engine + summary). Single responsibility: render the fixed-tariff fee report.
- Create: `docs/templates/reports/2_выписки_по_командам_взнос_10процентов.html` — variant 3 report (copy of variant 2, `[fee-config]` swapped to per-day ЧСФО/ПСФО).
- Create: `team_fee_preview.py` (repo root, temporary) — `render_fee(template_rel, race)` + `VARIANTS`; `__main__` renders every existing variant and opens each in a browser. Reuses `load_sample_race`, `REPO_ROOT`, `TEMPLATES_DIR` from `team_extract_preview.py`.
- Create: `tests/test_team_fee_report.py` (temporary) — render-smoke + structural-token checks for both variants.

The cloned template already carries these anchors (from the extract report):
`// [helpers]`, `// [transforms]`, `// [data]`, `// [render]`, `// [pagination]`, `// [selftest]`, `// [main]`, `/* [base-css] */`, `/* [page-css] */`.
This plan adds two anchors: the `// [fee-config]` block (right after the `var race = …;` line) and a `// [fee]` logic section (between `// [transforms]` and `// [data]`).

---

### Task 0: Create the worktree

**Files:** none (git only).

- [ ] **Step 1: Create the worktree off `ank/entry-template`**

Run (Git Bash):
```bash
cd "C:/Users/ank/Documents/Prog/SportOrg/pysport"
git rev-parse --verify ank/entry-template     # must succeed (finished extract report lives here)
git worktree add -b ank/entry-fee \
  "C:/Users/ank/Documents/Prog/SportOrg/worktree/pysport-entry-fee" ank/entry-template
```
Expected: `Preparing worktree (new branch 'ank/entry-fee')`; the directory is created.

- [ ] **Step 2: Sync the environment in the worktree**

Run:
```bash
cd "C:/Users/ank/Documents/Prog/SportOrg/worktree/pysport-entry-fee"
uv sync --frozen
```
Expected: environment resolves; no errors.

- [ ] **Step 3: Confirm the inherited base artifacts are present**

Run:
```bash
ls "docs/templates/reports/2_выписки_по_командам_регистрация.html" team_extract_preview.py tests/test_team_extract_report.py
```
Expected: all three paths exist (the fee report clones the first; the preview reuses the second).

> All subsequent paths are relative to the worktree root, and all commands run there.

---

### Task 1: Scaffold — clone the base report, preview harness, smoke test

**Files:**
- Create: `docs/templates/reports/2_выписки_по_командам_взнос.html` (copy of the extract report)
- Create: `team_fee_preview.py`
- Create: `tests/test_team_fee_report.py`

**Interfaces:**
- Consumes: `team_extract_preview.load_sample_race() -> dict`, `team_extract_preview.REPO_ROOT`, `team_extract_preview.TEMPLATES_DIR`.
- Produces: `team_fee_preview.render_fee(template_rel: str, race: dict) -> str`; `team_fee_preview.VARIANTS: list[str]`.

- [ ] **Step 1: Clone the extract template as the variant-2 file**

Run:
```bash
cp "docs/templates/reports/2_выписки_по_командам_регистрация.html" \
   "docs/templates/reports/2_выписки_по_командам_взнос.html"
```
Expected: the new file exists, byte-identical to the extract report (starting point; the fee changes come next).

- [ ] **Step 2: Write the preview harness**

Create `team_fee_preview.py`:
```python
"""TEMPORARY dev tool: render the fee report templates from a SportOrg race file.

Delete together with tests/test_team_fee_report.py when the templates are done.
"""
from __future__ import annotations

import os
import webbrowser
from typing import Any, Dict

from sportorg import config
from sportorg import settings as sportorg_settings
from sportorg.common.template import get_text_from_file
from team_extract_preview import REPO_ROOT, TEMPLATES_DIR, load_sample_race

VARIANTS = [
    "reports/2_выписки_по_командам_взнос.html",
    "reports/2_выписки_по_командам_взнос_10процентов.html",
]


def render_fee(template_rel: str, race: Dict[str, Any]) -> str:
    """Render one fee template with the same context the report dialog uses."""
    sportorg_settings.SETTINGS.templates_path = TEMPLATES_DIR
    return get_text_from_file(
        template_rel,
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
    for rel in VARIANTS:
        path = os.path.join(TEMPLATES_DIR, rel.replace("/", os.sep))
        if not os.path.exists(path):
            continue
        html = render_fee(rel, race)
        out = os.path.join(REPO_ROOT, os.path.basename(rel).replace(".html", "_preview.html"))
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote", out)
        webbrowser.open("file:///" + out.replace("\\", "/") + "?selftest")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the failing smoke test**

Create `tests/test_team_fee_report.py`:
```python
"""TEMPORARY: render-smoke + structural checks for the fee report templates."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from team_extract_preview import load_sample_race  # noqa: E402
from team_fee_preview import VARIANTS, render_fee  # noqa: E402


def _html(rel: str) -> str:
    return render_fee(rel, load_sample_race())


def test_variant2_renders() -> None:
    html = _html(VARIANTS[0])
    assert "var race" in html
    assert "<table" in html
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
uv run pytest tests/test_team_fee_report.py -q
```
Expected: PASS (1 passed). The cloned file still renders as the extract report at this point.

- [ ] **Step 5: Commit**

```bash
git add team_fee_preview.py tests/test_team_fee_report.py "docs/templates/reports/2_выписки_по_командам_взнос.html"
git commit -m "feat(report): scaffold fee report from team extracts clone + harness"
```

---

### Task 2: Fee config + pure fee/day functions + self-test

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_взнос.html` (`var race` line, `// [transforms]`→ new `// [fee]`, `// [selftest]`, `<title>`)
- Modify: `tests/test_team_fee_report.py`

**Interfaces:**
- Produces (JS): globals `EVENT_DAYS`, `CHIP_PER_DAY`, `CHIP_PER_DAY_BK`, `CHIP_BK_MARK`, `TARIFF`; functions `parseDays(comment, eventDays) -> {in:int, out:int}`, `hasBk(comment) -> bool`, `buildGroupIndex() -> {groupName:entry}`, `groupIndexOf() -> {groupName:entry}` (memoized), `startFeeFor(entry, daysIn, daysOut) -> number`, `chipFeeFor(comment, isRented, daysIn) -> number`, `feeForPerson(person, groupIndex, eventDays) -> {entry, daysIn, daysOut, start, chip, total, unknown}`, `formatMoney(n) -> string`. A tariff `entry` is `{name, groups, tariffTotal?, tariffPerDay?, tariffPerAbsentDay?}`.

- [ ] **Step 1: Set the title**

Replace the `<title>` line:
```html
<title>Выписки по командам — взнос</title>
```

- [ ] **Step 2: Insert the `[fee-config]` block right after the `var race = …;` line**

The file has:
```javascript
var race = {% endraw %}{{ race | tojson }}{% raw %};

// [helpers]
```
Insert between the `var race …;` line and `// [helpers]`:
```javascript
// ======================= [fee-config] ПРАВЬ ЗДЕСЬ =======================
var EVENT_DAYS = 3;            // всего дней соревнований (константа)

// Аренда чипа за день участия. Два тарифа: обычный и «бк» (маркер в комментарии).
var CHIP_PER_DAY    = 100;     // обычный чип
var CHIP_PER_DAY_BK = 150;     // чип «бк» (комментарий содержит CHIP_BK_MARK)
var CHIP_BK_MARK    = 'бк';    // маркер «бк» в комментарии (поиск без учёта регистра)

// Тарифы по категориям. У каждой: name (метка сводки), groups (ТОЧНЫЙ белый список
// имён групп — должны совпадать с race.groups) и поле тарифа, имя которого задаёт смысл:
//   tariffTotal                      -> за все дни (фиксированный)
//   tariffPerDay                     -> за день участия
//   tariffPerDay + tariffPerAbsentDay-> день участия + день неучастия
var TARIFF = {
  'ЧСФО':   { name: 'ЧСФО', tariffTotal: 1650, groups: ['МА', 'ЖА'] },
  'ПСФО':   { name: 'ПСФО', tariffTotal: 1200, groups: ['М18','Ж18','М16','Ж16','М14','Ж14'] },
  'РС-200': { name: 'РС',   tariffPerDay: 200,  groups: ['М35','Ж35','М45','Ж45','М55','Ж55','М65+','Ж65+'] },
  'РС-150': { name: 'РС',   tariffPerDay: 150,  groups: ['М12','Ж12','М10','Ж10'] }
};
// =======================================================================
```

- [ ] **Step 3: Add the `[fee]` logic section immediately before `// [data]`**

Insert this block just before the `// [data]` anchor:
```javascript
// [fee]
// Days from the "С:" code in the comment. Digits = participation days;
// '?','-','x' or any non-digit = non-participation. No code -> all EVENT_DAYS.
function parseDays(comment, eventDays) {
  var m = /[СC]:(\S+)/.exec(comment || '');
  if (!m) return { in: eventDays, out: 0 };
  var tok = m[1], din = 0;
  for (var i = 0; i < tok.length; i++) if (tok[i] >= '0' && tok[i] <= '9') din++;
  if (din > eventDays) din = eventDays;
  return { in: din, out: eventDays - din };
}

function hasBk(comment) {
  return String(comment || '').toLowerCase().indexOf(CHIP_BK_MARK.toLowerCase()) >= 0;
}

// group name -> tariff entry (reverse index of TARIFF.groups), memoized.
var GROUP_INDEX = null;
function buildGroupIndex() {
  var idx = {};
  for (var k in TARIFF) {
    if (!TARIFF.hasOwnProperty(k)) continue;
    var e = TARIFF[k];
    for (var i = 0; i < e.groups.length; i++) idx[e.groups[i]] = e;
  }
  return idx;
}
function groupIndexOf() {
  if (!GROUP_INDEX) GROUP_INDEX = buildGroupIndex();
  return GROUP_INDEX;
}

// Start fee: branch on which tariff field the entry carries.
function startFeeFor(entry, daysIn, daysOut) {
  if (!entry) return 0;                                   // unknown group
  if (entry.tariffTotal != null) return entry.tariffTotal;
  if (entry.tariffPerAbsentDay != null)
    return entry.tariffPerDay * daysIn + entry.tariffPerAbsentDay * daysOut;
  return entry.tariffPerDay * daysIn;
}

function chipFeeFor(comment, isRented, daysIn) {
  if (!isRented) return 0;
  return (hasBk(comment) ? CHIP_PER_DAY_BK : CHIP_PER_DAY) * daysIn;
}

function feeForPerson(p, groupIndex, eventDays) {
  var entry = p.group ? groupIndex[p.group.name] : null;
  var d = parseDays(p.comment, eventDays);
  var start = startFeeFor(entry, d.in, d.out);
  var chip = chipFeeFor(p.comment, p.is_rented_card, d.in);
  return { entry: entry, daysIn: d.in, daysOut: d.out,
           start: start, chip: chip, total: start + chip, unknown: !entry };
}

function formatMoney(n) {
  n = Math.round(n || 0);
  var neg = n < 0; if (neg) n = -n;
  var s = String(n), out = '';
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 === 0) out += ' ';
    out += s[i];
  }
  return (neg ? '-' : '') + out + ' ₽';   // ₽ = ₽
}
```

- [ ] **Step 4: Replace the whole `runSelfTest` body (after `// [selftest]`) with fee vectors**

Replace the existing `function runSelfTest() { … }` with:
```javascript
function runSelfTest() {
  var NB = ' ', RUB = '₽';
  var fails = [];
  function eq(name, got, want) {
    if (got !== want) fails.push(name + '=' + JSON.stringify(got) + ' want ' + JSON.stringify(want));
  }
  function pd(c) { var d = parseDays(c, 3); return d.in + '/' + d.out; }

  // parseDays (EVENT_DAYS assumed 3 here)
  eq('pd(123)', pd('С:123'), '3/0');
  eq('pd(1?3)', pd('С:1?3'), '2/1');
  eq('pd(?23)', pd('С:?23'), '2/1');
  eq('pd(12x)', pd('С:12x'), '2/1');
  eq('pd(??3)', pd('С:??3'), '1/2');
  eq('pd(???)', pd('С:???'), '0/3');
  eq('pd(tail)', pd('С:1?3 в/к'), '2/1');
  eq('pd(none)', pd('привет'), '3/0');
  eq('pd(empty)', pd(''), '3/0');

  // startFeeFor — explicit entries (variant-independent)
  eq('chsfo flat', startFeeFor({ tariffTotal: 1650 }, 1, 2), 1650);
  eq('psfo flat',  startFeeFor({ tariffTotal: 1200 }, 3, 0), 1200);
  eq('rs200x3',    startFeeFor({ tariffPerDay: 200 }, 3, 0), 600);
  eq('rs150x2',    startFeeFor({ tariffPerDay: 150 }, 2, 1), 300);
  eq('chsfo daily', startFeeFor({ tariffPerDay: 550, tariffPerAbsentDay: 55 }, 2, 1), 1155);
  eq('psfo daily',  startFeeFor({ tariffPerDay: 400, tariffPerAbsentDay: 40 }, 1, 2), 480);
  eq('unknown',    startFeeFor(null, 3, 0), 0);

  // chipFeeFor (CHIP_PER_DAY=100, CHIP_PER_DAY_BK=150)
  eq('chip off', chipFeeFor('С:123', false, 3), 0);
  eq('chip 3d',  chipFeeFor('С:123', true, 3), 300);
  eq('chip bk',  chipFeeFor('С:12x бк', true, 2), 300);
  eq('chip BK',  chipFeeFor('БК', true, 1), 150);

  // formatMoney
  eq('money', formatMoney(16500), '16' + NB + '500' + NB + RUB);
  eq('money0', formatMoney(0), '0' + NB + RUB);

  var banner = document.createElement('div');
  banner.className = 'selftest-banner';
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:6px;z-index:9999;font-family:monospace;'
    + (fails.length ? 'background:#fbb;color:#900;' : 'background:#bfb;color:#060;');
  banner.textContent = fails.length ? ('SELFTEST FAIL: ' + fails.join(' | ')) : 'SELFTEST OK';
  document.body.appendChild(banner);
  if (fails.length) console.error(fails); else console.log('SELFTEST OK');
}
```

- [ ] **Step 5: Verify the self-test PASSES in the browser**

Run:
```bash
uv run python team_fee_preview.py
```
Expected: a browser tab opens with a **green** `SELFTEST OK` banner at the top; console prints `SELFTEST OK`. (The table below still renders extract-style — Допуск present, no Взнос yet — that is fixed in Task 3.)

- [ ] **Step 6: Extend the pytest with fee-function token checks**

Append to `tests/test_team_fee_report.py`:
```python
def test_fee_functions_present() -> None:
    html = _html(VARIANTS[0])
    for token in [
        "[fee-config]", "var TARIFF", "function parseDays",
        "function startFeeFor", "function chipFeeFor", "function feeForPerson",
        "function formatMoney", "runSelfTest",
    ]:
        assert token in html
```

- [ ] **Step 7: Run the tests**

Run:
```bash
uv run pytest tests/test_team_fee_report.py -q
```
Expected: PASS (2 passed).

- [ ] **Step 8: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_взнос.html" tests/test_team_fee_report.py
git commit -m "feat(report): add fee config, pure fee/day functions, self-test"
```

---

### Task 3: Columns — drop Допуск, add Комментарий + Взнос, per-person fee

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_взнос.html` (`// [transforms]`, `// [render]`, `/* [base-css] */`)
- Modify: `tests/test_team_fee_report.py`

**Interfaces:**
- Consumes: `feeForPerson`, `groupIndexOf`, `formatMoney`, `formatZabeg`, `Qualification`, `EVENT_DAYS`.
- Produces (JS): updated `COLS` (no `dopusk`; `note` titled «Комментарий»; new `fee`), updated `cellValues(slot, chipCounts) -> {…, fee, _chipDup, _unknown}`.

- [ ] **Step 1: Remove the Допуск transform (in `// [transforms]`)**

Delete these two items entirely (the `DOPUSK_LETTERS` array and the `formatDopusk` function); keep `formatZabeg`:
```javascript
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

- [ ] **Step 2: Replace the `COLS` array (in `// [render]`)**

Replace the existing `var COLS = [ … ];` with (Допуск gone; «Примечание»→«Комментарий» stays before the new «Взнос»):
```javascript
var COLS = [
  { key: 'index', title: '№',                     width: '2.4',  align: 'right',  cls: 'c-index' },
  { key: 'fio',   title: 'Фамилия, имя, отчество', width: '34.3', align: 'left',   cls: 'c-fio' },
  { key: 'zabeg', title: 'Забег',                  width: '3.9',  align: 'center', cls: 'c-zabeg' },
  { key: 'birth', title: 'Дата рождения',          width: '10.8', align: 'center', cls: 'c-birth' },
  { key: 'group', title: 'Группа',                 width: '4.5',  align: 'center', cls: 'c-group' },
  { key: 'qual',  title: 'Квал',                   width: '4.9',  align: 'center', cls: 'c-qual' },
  { key: 'chip',  title: 'Чип',                    width: '9.4',  align: 'center', cls: 'c-chip' },
  { key: 'note',  title: 'Комментарий',            width: '',     align: 'left',   cls: 'c-note' },
  { key: 'fee',   title: 'Взнос',                  width: '8',    align: 'right',  cls: 'c-fee' }
];
```

- [ ] **Step 3: Replace `cellValues` (in `// [render]`)**

Replace the existing `function cellValues(slot, chipCounts) { … }` with:
```javascript
function cellValues(slot, chipCounts) {
  if (slot.type !== 'data') return null;
  var p = slot.person;
  var card = p.card_number | 0;
  var f = feeForPerson(p, groupIndexOf(), EVENT_DAYS);
  return {
    index: String(slot.index),
    fio: fioOf(p),
    zabeg: formatZabeg(p.start_group),
    birth: p.birthday || '',
    group: slot.groupName || '',
    qual: Qualification[p.qual] || '',
    chip: card > 0 ? String(card) : '',
    note: p.comment || '',
    fee: formatMoney(f.total),
    _chipDup: card > 0 && chipCounts[card] > 1,
    _unknown: f.unknown
  };
}
```

- [ ] **Step 4: Highlight the unknown-group cell (in `buildTable`, `// [render]`)**

In `buildTable`, the per-cell loop currently reads:
```javascript
      if (vals) {
        td.textContent = vals[c.key] || '';
        if (c.key === 'chip' && vals._chipDup) td.className += ' chip-dup';
      }
```
Replace it with (adds the unknown-group highlight on the «Группа» cell):
```javascript
      if (vals) {
        td.textContent = vals[c.key] || '';
        if (c.key === 'chip' && vals._chipDup) td.className += ' chip-dup';
        if (c.key === 'group' && vals._unknown) td.className += ' fee-unknown';
      }
```

- [ ] **Step 5: Swap the Допуск CSS rule for fee/unknown rules (in `/* [base-css] */`)**

Replace the Допуск rule:
```css
table.extract .c-dopusk { font-family: "Courier New", monospace; white-space: pre; vertical-align: middle; }
```
with:
```css
table.extract td.c-fee { font-variant-numeric: tabular-nums; }
td.fee-unknown { background: #ffd; }   /* unknown group — взнос не посчитан */
```

- [ ] **Step 6: Verify in the browser**

Run:
```bash
uv run python team_fee_preview.py
```
Expected:
- «Допуск» column is gone; «Комментарий» sits where it was; a right-aligned «Взнос» column is last, showing money like `600 ₽` / `1 650 ₽` (values depend on the sample's groups/comments).
- Groups not in `TARIFF` show a pale-yellow «Группа» cell and a `0 ₽`-plus-chip fee (the sample race may have many unknown groups — that is expected; the JS self-test is the source of truth for the math).
- Self-test banner still green.

> To see meaningful fees, point the preview at a real registration race:
> `SPORTORG_RACE="C:/path/to/race.json" uv run python team_fee_preview.py`
> (`load_sample_race` accepts the `SPORTORG_RACE` env var via `team_extract_preview`; if it does not in your checkout, pass the path by editing the `main()` call.)

- [ ] **Step 7: Extend the pytest with column checks**

Append to `tests/test_team_fee_report.py`:
```python
def test_variant2_columns() -> None:
    html = _html(VARIANTS[0])
    assert "Взнос" in html
    assert "Комментарий" in html
    assert "Допуск" not in html
    assert "formatDopusk" not in html
    assert "fee-unknown" in html
```

- [ ] **Step 8: Run the tests**

Run:
```bash
uv run pytest tests/test_team_fee_report.py -q
```
Expected: PASS (3 passed).

- [ ] **Step 9: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_взнос.html" tests/test_team_fee_report.py
git commit -m "feat(report): fee column, drop Допуск, per-person взнос with unknown highlight"
```

---

### Task 4: Per-team summary + pagination + main wiring

**Files:**
- Modify: `docs/templates/reports/2_выписки_по_командам_взнос.html` (`// [fee]`, `// [render]`, `// [pagination]`, `// [main]`, `/* [base-css] */`)
- Modify: `tests/test_team_fee_report.py`

**Interfaces:**
- Consumes: `feeForPerson`, `hasBk`, `formatMoney`, `groupIndexOf`, `buildTeamSlots`, `buildSlots`, `paginate`, `buildPage`, `buildChipCounts`, `racePreparation`, `TARIFF`, `EVENT_DAYS`, `CHIP_PER_DAY`, `CHIP_PER_DAY_BK`.
- Produces (JS): `buildTeamSummary(members, groupIndex, eventDays) -> slot[]` where a summary slot is `{type:'summary', text:string, cls:string}`; `buildPage`/`buildTable`/`paginate` extended to handle summary slots.

- [ ] **Step 1: Add `buildTeamSummary` at the end of the `// [fee]` section**

```javascript
// Per-team summary slots: one line per TARIFF category (by key order), chips line,
// optional unknown-groups line, divider, total. Rendered as full-width table rows.
function buildTeamSummary(members, groupIndex, eventDays) {
  var order = [], agg = {};
  for (var k in TARIFF) {
    if (!TARIFF.hasOwnProperty(k)) continue;
    order.push(k);
    agg[k] = { name: TARIFF[k].name, people: 0, sum: 0, days: {} };
  }
  var chipCount = 0, chipSum = 0, chipByRate = {}, unknownCount = 0, totalSum = 0;

  for (var i = 0; i < members.length; i++) {
    var p = members[i];
    var f = feeForPerson(p, groupIndex, eventDays);
    totalSum += f.total;
    if (f.entry) {
      var key = null;
      for (var o = 0; o < order.length; o++) { if (TARIFF[order[o]] === f.entry) { key = order[o]; break; } }
      var a = agg[key];
      a.people++; a.sum += f.start;
      a.days[f.daysIn] = (a.days[f.daysIn] || 0) + 1;
    } else {
      unknownCount++;
    }
    if (p.is_rented_card) {
      var rate = hasBk(p.comment) ? CHIP_PER_DAY_BK : CHIP_PER_DAY;
      chipCount++; chipSum += f.chip;
      chipByRate[rate] = (chipByRate[rate] || 0) + 1;
    }
  }

  function daysDetail(days) {
    var keys = Object.keys(days).map(Number).sort(function (a, b) { return b - a; });
    if (!keys.length) return '';
    var parts = [];
    for (var i = 0; i < keys.length; i++) parts.push(keys[i] + ' дн.: ' + days[keys[i]] + ' чел.');
    return '  (' + parts.join('; ') + ')';
  }

  var slots = [];
  function line(text, cls) { slots.push({ type: 'summary', text: text, cls: cls || '' }); }

  for (var oo = 0; oo < order.length; oo++) {
    var a2 = agg[order[oo]];
    if (!a2.people) continue;
    line(a2.name + ': ' + a2.people + ' чел., ' + formatMoney(a2.sum) + daysDetail(a2.days));
  }
  if (chipCount) {
    var tail = '', rates = Object.keys(chipByRate).map(Number).sort(function (a, b) { return a - b; });
    if (rates.length > 1) {
      var rp = [];
      for (var r = 0; r < rates.length; r++) rp.push(formatMoney(rates[r]) + '/дн.: ' + chipByRate[rates[r]]);
      tail = '  (' + rp.join('; ') + ')';
    }
    line('Аренда чипов: ' + chipCount + ' шт., ' + formatMoney(chipSum) + tail);
  }
  if (unknownCount) line('Неизвестные группы: ' + unknownCount + ' чел. — взнос не посчитан', 'sum-warn');
  line('', 'sum-divider');
  line('Итого: ' + formatMoney(totalSum), 'sum-total');
  return slots;
}
```

- [ ] **Step 2: Render summary rows in `buildTable` (in `// [render]`)**

In `buildTable`, the row loop starts with:
```javascript
  var tbody = document.createElement('tbody');
  rows.forEach(function (slot) {
    var tr = document.createElement('tr');
    tr.className = slot.type === 'data' ? 'row-data' : 'row-empty';
```
Insert a summary branch at the very top of the `forEach` callback (before that `var tr = …`):
```javascript
  var tbody = document.createElement('tbody');
  rows.forEach(function (slot) {
    if (slot.type === 'summary') {
      var str = document.createElement('tr');
      str.className = 'row-summary ' + (slot.cls || '');
      var std = document.createElement('td');
      std.colSpan = COLS.length;
      std.textContent = slot.text || '';
      str.appendChild(std);
      tbody.appendChild(str);
      return;
    }
    var tr = document.createElement('tr');
    tr.className = slot.type === 'data' ? 'row-data' : 'row-empty';
```

- [ ] **Step 3: Keep the summary block whole in `paginate` (in `// [pagination]`)**

Replace the existing `function paginate(slots) { … }` with (adds the summary keep-whole rule; the rest is unchanged):
```javascript
function paginate(slots) {
  var pages = [];
  var i = 0;
  var sumStart = -1;
  for (var s = 0; s < slots.length; s++) { if (slots[s].type === 'summary') { sumStart = s; break; } }
  while (i < slots.length) {
    while (i < slots.length && slots[i].separator) i++;   // drop separators at page top
    if (i >= slots.length) break;
    var take = Math.min(ROWS_PER_PAGE, slots.length - i);
    take = applyKeepMin(slots, i, take);
    // summary is the trailing run; keep it whole: if the slice would include only
    // part of it, break right before it so it starts fresh on the next page.
    if (sumStart >= 1 && i < sumStart && i + take > sumStart && i + take < slots.length) {
      take = sumStart - i;
    }
    var slice = slots.slice(i, i + take);
    while (slice.length && slice[slice.length - 1].separator) slice.pop();   // no trailing separator
    while (slice.length < ROWS_PER_PAGE) slice.push({ type: 'empty' });      // fill to bottom
    pages.push(slice);
    i += take;
  }
  return pages;
}
```

- [ ] **Step 4: Replace the `// [main]` body to append the per-team summary**

Replace the existing `document.addEventListener('DOMContentLoaded', function () { … });` with:
```javascript
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('selftest') >= 0) runSelfTest();
  racePreparation(race);
  var chipCounts = buildChipCounts(race.persons);
  var gi = groupIndexOf();
  var root = document.getElementById('report');
  root.innerHTML = '';

  function renderBlock(team, members, slots) {
    if (!slots.length) return;
    var all = slots.concat([{ type: 'empty', separator: true }])
                   .concat(buildTeamSummary(members, gi, EVENT_DAYS));
    var pages = paginate(all);
    for (var pi = 0; pi < pages.length; pi++) root.appendChild(buildPage(team, pages[pi], chipCounts));
  }

  for (var oi = 0; oi < race.organizations.length; oi++) {
    var team = race.organizations[oi];
    var members = race.persons.filter(function (p) { return p.organization && p.organization.id === team.id; });
    if (!members.length) continue;
    renderBlock(team, members, buildTeamSlots(team, race));
  }

  // Trailing "no team" block (athletes without an organization).
  var noTeam = race.persons.filter(function (p) { return !p.organization; });
  if (noTeam.length) renderBlock({ name: 'Без команды' }, noTeam, buildSlots(noTeam, race));
});
```

- [ ] **Step 5: Add summary-row CSS (after `/* [base-css] */`, near the fee rules)**

```css
tr.row-summary td {
  text-align: left;
  white-space: nowrap;
  font-size: 10pt;
  border-left: 1px solid #000;
  border-right: 1px solid #000;
  vertical-align: middle;
  height: 6mm;
}
tr.sum-warn td   { color: #900; }
tr.sum-total td  { font-weight: bold; border-top: 1px solid #000; }
tr.sum-divider td { height: 0; padding: 0; border-top: 1px solid #000; }
```

- [ ] **Step 6: Verify on screen**

Run:
```bash
uv run python team_fee_preview.py
```
Expected:
- Under each team's rows: a blank separator row, then category lines (only non-empty categories), an «Аренда чипов» line when any chip is rented, an optional red «Неизвестные группы …» line, a divider, and a bold «Итого …».
- «Итого» equals the sum of the «Взнос» column for that team (spot-check one small team by hand).
- Self-test banner still green.

- [ ] **Step 7: Verify in print preview**

In the opened browser press `Ctrl+P`:
- The summary block stays together — never split across a page boundary.
- Pages still fill to the bottom; each team starts on a new page; the self-test banner is hidden.
- If a team's rows exactly fill a page, its summary moves wholly to the next page.

- [ ] **Step 8: Extend the pytest with summary checks**

Append to `tests/test_team_fee_report.py`:
```python
def test_variant2_summary() -> None:
    html = _html(VARIANTS[0])
    for token in ["function buildTeamSummary", "row-summary", "Итого:", "Аренда чипов:", "sum-total"]:
        assert token in html
```

- [ ] **Step 9: Run the tests**

Run:
```bash
uv run pytest tests/test_team_fee_report.py -q
```
Expected: PASS (4 passed).

- [ ] **Step 10: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_взнос.html" tests/test_team_fee_report.py
git commit -m "feat(report): per-team fee summary with chips, unknown, total"
```

---

### Task 5: Variant 3 (per-day, 10%) + finalize

**Files:**
- Create: `docs/templates/reports/2_выписки_по_командам_взнос_10процентов.html`
- Modify: `tests/test_team_fee_report.py`

- [ ] **Step 1: Copy variant 2 to variant 3**

Run:
```bash
cp "docs/templates/reports/2_выписки_по_командам_взнос.html" \
   "docs/templates/reports/2_выписки_по_командам_взнос_10процентов.html"
```

- [ ] **Step 2: Set the variant-3 title**

In `2_выписки_по_командам_взнос_10процентов.html` replace the `<title>` line:
```html
<title>Выписки по командам — взнос (подневный)</title>
```

- [ ] **Step 3: Swap the `TARIFF` literal in `[fee-config]`**

In `2_выписки_по_командам_взнос_10процентов.html`, replace the entire `var TARIFF = { … };` block with (ЧСФО/ПСФО become per-day; non-participation day ≈ 10 % of the participation day; РС unchanged):
```javascript
var TARIFF = {
  'ЧСФО':   { name: 'ЧСФО', tariffPerDay: 550, tariffPerAbsentDay: 55, groups: ['МА', 'ЖА'] },
  'ПСФО':   { name: 'ПСФО', tariffPerDay: 400, tariffPerAbsentDay: 40, groups: ['М18','Ж18','М16','Ж16','М14','Ж14'] },
  'РС-200': { name: 'РС',   tariffPerDay: 200,  groups: ['М35','Ж35','М45','Ж45','М55','Ж55','М65+','Ж65+'] },
  'РС-150': { name: 'РС',   tariffPerDay: 150,  groups: ['М12','Ж12','М10','Ж10'] }
};
```
Leave `EVENT_DAYS`, the three `CHIP_*` constants, and everything else untouched.

- [ ] **Step 4: Verify variant 3 in the browser**

Run:
```bash
uv run python team_fee_preview.py
```
Expected: a second browser tab opens for variant 3 with a **green** `SELFTEST OK` banner (the self-test is identical and passes because it uses explicit tariff entries). ЧСФО/ПСФО fees now vary with participation days; РС and chip identical to variant 2.

- [ ] **Step 5: Extend the pytest to cover variant 3**

Append to `tests/test_team_fee_report.py`:
```python
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


def test_both_standalone_no_external_refs() -> None:
    for rel in VARIANTS:
        html = _html(rel)
        assert "<script src=" not in html
        assert "<link " not in html
        assert 'src="http' not in html
```

- [ ] **Step 6: Run the full fee test suite**

Run:
```bash
uv run pytest tests/test_team_fee_report.py -q
```
Expected: PASS (all fee tests green).

- [ ] **Step 7: Format + lint**

Run:
```bash
uv run poe format
uv run poe lint
```
Expected: no errors (the preview script and test are formatted/linted).

- [ ] **Step 8: Manual acceptance checklist (browser, both variants)**

Run `uv run python team_fee_preview.py` (ideally with `SPORTORG_RACE` pointed at a real registration race) and confirm against the spec:
- [ ] Columns: «Допуск» gone; «Комментарий» in its place; right-aligned «Взнос» last.
- [ ] Взнос per person = start fee + chip rental; the column sums to the team «Итого».
- [ ] Variant 2: ЧСФО 1650 / ПСФО 1200 flat; РС 200/150 × participation days.
- [ ] Variant 3: ЧСФО 550/55, ПСФО 400/40 per participation/non-participation day; РС unchanged.
- [ ] Chip: 100 ₽/day, or 150 ₽/day when the comment contains «бк»; only when «аренда чипа» is set.
- [ ] Days parsed from the «С:» code; no code → all EVENT_DAYS.
- [ ] Per-team summary: category lines (two РС lines), chips line (per-rate breakdown when mixed), optional unknown-groups line, divider, bold «Итого»; block never split across pages.
- [ ] Self-test banner green on both; hidden in print; each team on its own page; pages fill to the bottom.

- [ ] **Step 9: Commit**

```bash
git add "docs/templates/reports/2_выписки_по_командам_взнос_10процентов.html" tests/test_team_fee_report.py
git commit -m "feat(report): add per-day (10%) fee variant and finalize tests"
```

- [ ] **Step 10: Deployment note (no code change)**

Both reports are standalone single files. To use them in SportOrg, copy `2_выписки_по_командам_взнос.html` and `2_выписки_по_командам_взнос_10процентов.html` into the templates folder under `reports/` (the folder `settings.templates_path` points at). They then appear in the «Создание протокола» dialog. The author handles the final relocation (as with the extract report).

---

## Self-Review

**Spec coverage:**
- Two files, clones of the extract report, differ only in `[fee-config]` → Task 1 (clone), Task 5 (variant-3 copy + TARIFF swap); Global Constraints.
- Columns: drop Допуск, Комментарий to its place, append Взнос → Task 3 (`COLS`, `cellValues`, CSS).
- `TARIFF` keyed by category with `groups` + semantic tariff field names → Task 2 (`[fee-config]`), Task 5 (variant 3).
- Days from «С:» code (digits = participation; no code → all days; cap at EVENT_DAYS) → Task 2 (`parseDays`) + self-test vectors.
- Start fee (flat / per-day / per-day+absent) branched by field presence → Task 2 (`startFeeFor`) + self-test.
- Chip rental two tariffs (100 / 150 «бк»), per participation day, only if `is_rented_card` → Task 2 (`chipFeeFor`, `hasBk`) + self-test.
- Взнос = start + chip; column sums to Итого → Task 3 (`cellValues.fee` = `feeForPerson.total`) + Task 4 total.
- Unknown group → 0 fee + highlight + summary line; chip still counted → Task 3 (`_unknown`, `fee-unknown`), Task 4 (`unknownCount`).
- Per-team summary (category lines incl. two РС, chips line with per-rate breakdown, day detail, divider, Итого; no grand total) → Task 4 (`buildTeamSummary`).
- Summary as trailing full-width table rows, block not split → Task 4 (`buildTable` summary branch, `paginate` keep-whole, CSS).
- Standalone output, no base_v2 dependency, embedded race JSON → inherited from clone + Task 5 `test_both_standalone_no_external_refs`.
- Load via SportOrg deserializer → reuse `team_extract_preview.load_sample_race` (Task 1).
- Pagination Variant 1 (A4, 5mm, repeat header, fill, keep-≥3), «Без команды» block → inherited from clone, extended for summary in Task 4.

**Placeholder scan:** No TBD/TODO; every code step shows complete code; the only tuning note (Task 3 `SPORTORG_RACE`) is an optional convenience, not a required blank. ✓

**Type/name consistency:** `parseDays`→`{in,out}` consumed by `feeForPerson`/self-test; `startFeeFor(entry,daysIn,daysOut)`, `chipFeeFor(comment,isRented,daysIn)`, `feeForPerson(p,groupIndex,eventDays)→{entry,daysIn,daysOut,start,chip,total,unknown}`, `groupIndexOf()`, `formatMoney`, `buildTeamSummary(members,groupIndex,eventDays)→summary slots` used consistently across Tasks 2–4; summary slot shape `{type:'summary',text,cls}` produced in Task 4 Step 1 and consumed in Task 4 Steps 2–3; `COLS` (9 entries incl. `fee`, no `dopusk`) consistent between Task 3 and the `colSpan = COLS.length` summary rows. ✓

**Variant parity:** Only `<title>` and the `TARIFF` literal differ between the two files; the self-test uses explicit tariff entries, so it is valid and green in both. ✓
