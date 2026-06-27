# dev-ank → ank/dev Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the messy `dev-ank` branch as a new branch `ank/dev` (off `master`) where every feature is exactly one clean commit, while preserving everything so the final tree matches `dev-ank` byte-for-byte.

**Architecture:** Do not salvage `dev-ank`'s history. Branch `ank/dev` from `master` and reconstruct it from the net diff `git diff master..dev-ank`, one commit at a time. Files owned by a single feature are taken whole from `dev-ank`; files shared by several features are built up additively, slice by slice. A per-commit test gate keeps every commit green; per-file and final tree-equality checks guarantee faithful reconstruction.

**Tech Stack:** git, Python 3.8, `uv`, `poe` task runner, `pytest`, `ruff`.

## Global Constraints

- Base branch: `ank/dev` is created from `master` (`c11c36d9`). `master` == `origin/master` == `upstream/master` == merge-base with `dev-ank`.
- Build `ank/dev` in a dedicated git **worktree** (separate directory) so the `openspec-base` working tree — which holds all claude/openspec files (`CLAUDE.md`, `memory/`, `docs/superpowers`, `openspec/`, none of which exist on `master`/`dev-ank`) — is left untouched and cannot leak into `ank/dev`.
- Authoritative source of content: the net diff `git diff master..dev-ank` (dev-ank tip = `ab3559e0`). The dev-ank commit history is NOT used.
- Conventional Commits messages, present tense, no trailing period, ≤70 chars summary.
- Do NOT run `ruff format` or otherwise reformat — reproduce dev-ank content verbatim (it is already ruff-formatted; `[tool.ruff.lint] select = []` means no lint rules).
- Do NOT touch `dev-ank`, `master`, or any other branch. Do NOT push or open a PR.
- `.mo` files are gitignored — `generate-mo` never affects tree comparisons.
- Ignore `stash@{1}` ("On dev-ank: === dev-ank changes ==="); out of scope.

## Definitions: verification commands (used by every task)

- **Syntax check** (changed `.py` only): `python -c "import ast; ast.parse(open(r'PATH').read())"` → no output = OK.
- **Green check (intermediate):** `uv run poe test-fast` → exit 0 (runs `pytest -vv --exitfirst`, no coverage gate).
- **Per-file equality (closing commit):** `git diff dev-ank -- PATH` → empty output = file fully reconstructed.
- **Final tree equality (Task M only):** `git diff ank/dev dev-ank` → empty.
- **Full gate (Task M only):** `uv run poe test` (coverage ≥42%) and `uv run poe lint` → exit 0.

## Commit order (fixed)

`T1 relay-logic → T2 relay-display → T3 logging → T4 novosibirsk → T5 photo-controls → T6 live → T7 winorient → T8 time-fix → T9 marked-route → TE1 nizhni → TE2 pairs-v1 → TE3 classic → TE4 pairs-v2 → TE5 tomsk → TD docs → TM misc`

## Shared-file → commit map (the centerpiece)

Each shared file is built additively. "Closes at" = the last commit touching it; after that commit, `git diff dev-ank -- FILE` must be empty. Regions are identified by their enclosing symbol; read exact content from `git diff master dev-ank -- FILE`.

### `sportorg/models/memory.py` — closes at **TM**
| Region (anchor) | Commit |
|---|---|
| `class PrintableValue` (after `class SystemType`) | T4 |
| `Group.__init__`: `self.is_all_russian_competition = False` | T1 |
| `Group.set_type`: reset `is_all_russian_competition` | T1 |
| `Group.to_dict`: `"is_all_russian_competition"` key | T1 |
| `Group.update`: `self.is_all_russian_competition = bool(...)` | T1 |
| `Result.get_start_time`: `-> OTime` return annotation | TM |
| `ResultSportident.get_finish_time`: `nizhni_novgorod_relay = False` block | TE1 |
| `ResultSportident.check`: signature `course: Course = None` | T4 |
| `check`: `NOVOSIBIRSK_VYBOR_PAIRS = False` setup block | TE2 |
| `check`: `NOVOSIBIRSK_VYBOR_CLASSIC = False` block | TE3 |
| `check`: `if NOVOSIBIRSK_VYBOR_PAIRS and is_unique:` recognition block | TE2 |
| `check`: `if False and NOVOSIBIRSK_VYBOR_PAIRS:` block | TE2 |
| `check`: `tomsk_marked_route = False` block (commented DSQ near end) | TE5 |
| `Race.to_dict`: group-sort block (`order = {group.name: ...}`) | T2 |
| `Race.find_course`: `[c for c in self.courses if person.group.name in c.name]` | T4 |
| `RelayTeam.__lt__`: commented-out out-of-competition comparison | T1 |
| `RelayTeam`: remove old `get_is_team_placed`; add `get_is_team_placed(/, place_out_of_competition=False)` | T1 |
| `RelayTeam.get_is_out_of_competition`: drop `is_best_team_placing_mode` branch | T1 |
| `RelayTeam.get_is_mixed_team`: new method | T1 |

### `sportorg/models/result/result_checker.py` — closes at **TE4**
| Region | Commit |
|---|---|
| imports: `from sportorg import settings`, `from sportorg.common.levenshtein import levenshtein` | T4 |
| `is_any_course` branch: `return result.check(course)` | T4 |
| rogaine scoring fn: real `ROGAINE_SETTINGS`/`NOVOSIBIRSK_VYBOR` head block + scoring-loop changes (`cur_split.is_correct`, `LIMIT_NUM_CONTROLS`, `ignored_controls`, pairs-bonus loop) | T4 |
| rogaine scoring fn: the `NOVOSIBIRSK_VYBOR_PAIRS_V2 = False` block, **repeated 5× verbatim** | TE4 |
| `marked_route_check_penalty_laps` staticmethod | T9 |

### `sportorg/gui/dialogs/text_io.py` — closes at **T8**
| Region | Commit |
|---|---|
| photo-controls CSV hunks (anything referencing photo/controls/CSV column handling, `get_value_options`, photo `set_property` branches) | T5 |
| time-rounding hunk(s) (comma/round handling in time formatting) | T8 |

### `sportorg/gui/menu/actions.py` — closes at **T6**
| Region | Commit |
|---|---|
| `import os`; `ResultSportident` import; `photo_controls` import; `UpdatePhotoControlsAction` | T5 |
| `OnlineMultidaySendAll` | T6 |

### `sportorg/gui/menu/menu.py` — closes at **TM**
| Region | Commit |
|---|---|
| `"Update photo controls from CSV"` menu item | T5 |
| `"Send multiday start list and results"` menu item | T6 |
| duplicate `"shortcut": "Ctrl+E"` line | TM |

### `sportorg/settings.py` — closes at **T5**
| Region | Commit |
|---|---|
| `NOVOSIVIRSK_ROGAINE_PAIRS` field | T4 |
| `FEATURE_ROGAINE_PHOTO_CONTROLS` + `DEFAULT_FEATURES` entry + `rogaine_photo_controls_path` | T5 |

### `sportorg/modules/printing/printout_split.py` — closes at **TM**
| Region | Commit |
|---|---|
| `import settings`, `is_photo_mark`; title-by-`<br>`; "ФОТО КП" block | T5 |
| `tomsk_marked_route = False` (skip printing correct controls) | TE5 |
| commented Xprinter vertical-space block | TM |

### `sportorg/gui/main_window.py` — closes at **TM**
| Region | Commit |
|---|---|
| `photo_controls` import + apply-on-read block | T5 |
| `HuichangClient` import reorder | TM |

### `tests/test_penalty_checking.py` — closes at **T9**
| Region | Commit |
|---|---|
| added imports + `test_penalty_calculation_function` additions for marked-route penalty laps | T9 |
| (if any hunk tests rogaine pair scoring rather than marked-route, assign that hunk to T4) | T4 |

---

## Slice mechanics (how to apply a region subset)

Two reliable methods; pick per situation:

- **Whole-file (single-owner files):** `git show dev-ank:PATH > PATH` then `git add PATH`.
- **Region subset (shared files):** apply only that commit's hunks. Preferred:
  1. `git diff master dev-ank -- PATH > /tmp/full.patch`
  2. Copy the `diff --git`/`index`/`---`/`+++` header plus only the wanted `@@` hunks into `/tmp/slice.patch`.
  3. `git apply /tmp/slice.patch` (add `--3way` or `-C1` if context drifted).
  - For **interleaved** additions in one hunk (result_checker.py T4 vs TE4): instead build by subtraction — `git show dev-ank:PATH > PATH`, then delete the not-yet-wanted blocks with `Edit` (TE4's 5× `NOVOSIBIRSK_VYBOR_PAIRS_V2` blocks and T9's `marked_route_check_penalty_laps`) to produce the T4 state; re-add them in T9 and TE4 respectively.

After every commit's edits: run the **syntax check** on each changed `.py`, then the **green check**, then commit. At a file's **closing commit**, also run the **per-file equality** check.

---

## Task 0: Setup and baseline

**Files:** none (branch + scratch artifacts only)

- [ ] **Step 1: Confirm clean state and refs**

Run:
```bash
git status --short                      # expect empty
git rev-parse master ab3559e0 dev-ank   # master==c11c36d9; dev-ank tip==ab3559e0
```

- [ ] **Step 2: Create an isolated worktree for ank/dev**

Build in a separate directory so `openspec-base` (and every claude/openspec file) stays untouched and no stray untracked files can leak into `ank/dev`.
```bash
git worktree add C:/Users/ank/Documents/Prog/SportOrg/pysport-ankdev -b ank/dev master
cd C:/Users/ank/Documents/Prog/SportOrg/pysport-ankdev
```
Run all remaining tasks from this worktree directory. Then one-time environment setup (fresh `.venv`, deps are uv-cached):
```bash
uv sync --frozen
uv run python -c "from sportorg.common.otime import OTime; print(OTime(1))"
```
Expected: prints an OTime value. The Rust `sportorg_core` ext is NOT required — `otime.py` falls back to `PythonOTime` (`except ModuleNotFoundError`), no test references it, and master itself runs on the fallback. Skip `poe develop-rust`.

- [ ] **Step 3: Capture the dev-ank baseline (calibrates "green")**

```bash
git diff master dev-ank --stat        # 34 files, +2578 -249
git diff master dev-ank > C:/Users/ank/AppData/Local/Temp/claude/C--Users-ank-Documents-Prog-SportOrg-pysport/bb7265f2-29d4-4acf-9f3e-b7805a5cf7e8/scratchpad/netdiff.patch
```
Keep `netdiff.patch` as the authoritative reference for all region extraction.

- [ ] **Step 4: Sanity-run the suite on the base**

Run: `uv run poe test-fast`
Expected: exit 0 (master is green). If not, stop and report.

---

## Task 1: T1 — relay placing (all-Russian competition)

**Files:**
- Whole: `sportorg/models/result/result_calculation.py`, `tests/test_relay_results.py`, `changelog.md`, `changelog_ru.md`
- Region: `sportorg/models/memory.py` (T1 regions per map)

**Interfaces:**
- Produces: `Group.is_all_russian_competition: bool`; `RelayTeam.get_is_team_placed(/, place_out_of_competition=False)`, `RelayTeam.get_is_mixed_team()`; `ResultCalculation.sort_relay_all_russian_competition(teams)`.

- [ ] **Step 1: Take single-owner files whole**
```bash
git show dev-ank:sportorg/models/result/result_calculation.py > sportorg/models/result/result_calculation.py
git show dev-ank:tests/test_relay_results.py > tests/test_relay_results.py
git show dev-ank:changelog.md > changelog.md
git show dev-ank:changelog_ru.md > changelog_ru.md
```

- [ ] **Step 2: Apply memory.py T1 regions**
Read T1 regions from `netdiff.patch` (the `Group.*` and `RelayTeam.*` hunks listed in the map) and apply them to `sportorg/models/memory.py` via slice patch or `Edit`. Do NOT include any `NOVOSIBIRSK_*`, `nizhni`, `tomsk`, `PrintableValue`, `Race.to_dict`, `Race.find_course`, or `get_start_time` regions.

- [ ] **Step 3: Syntax check**
Run: `python -c "import ast; ast.parse(open(r'sportorg/models/memory.py').read())"`
Expected: no output.

- [ ] **Step 4: Green check**
Run: `uv run poe test-fast`
Expected: exit 0 (includes the new `tests/test_relay_results.py`).

- [ ] **Step 5: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(relay): place relay teams as in all-Russian competitions"
```

---

## Task 2: T2 — relay bib format and split display

**Files:**
- Whole: `sportorg/data/templates/script.js.html`, `sportorg/data/templates/split/1_сплиты_с_лидерами_на_перегонах.html`
- Region: `sportorg/models/memory.py` (`Race.to_dict` group-sort block)

- [ ] **Step 1: New/whole template files**
```bash
git show dev-ank:sportorg/data/templates/script.js.html > sportorg/data/templates/script.js.html
git show "dev-ank:sportorg/data/templates/split/1_сплиты_с_лидерами_на_перегонах.html" > "sportorg/data/templates/split/1_сплиты_с_лидерами_на_перегонах.html"
```

- [ ] **Step 2: Apply memory.py `Race.to_dict` group-sort region** (from netdiff.patch).

- [ ] **Step 3: Syntax check** memory.py (as Task 1 Step 3).

- [ ] **Step 4: Green check** — `uv run poe test-fast` → exit 0.

- [ ] **Step 5: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(results): relay bib format 15.1 and split display"
```

---

## Task 3: T3 — daily rotating log files

**Files:**
- Whole: `sportorg/logging.py` (new), `sportorg/config.py`, `sportorg/modules/sportident/backup.py`

**Interfaces:** Produces `sportorg.logging.DailyFileHandler`, `sportorg.logging.make_log_filename(prefix, suffix)`.

- [ ] **Step 1: Take files whole**
```bash
git show dev-ank:sportorg/logging.py > sportorg/logging.py
git show dev-ank:sportorg/config.py > sportorg/config.py
git show dev-ank:sportorg/modules/sportident/backup.py > sportorg/modules/sportident/backup.py
```

- [ ] **Step 2: Syntax check** all three changed `.py`.

- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.

- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(logging): daily rotating log files"
```

---

## Task 4: T4 — configurable Novosibirsk vybor scoring

**Files:**
- Whole: `sportorg/common/levenshtein.py` (new), `tests/test_levenshtein.py` (new), `sportorg/gui/dialogs/group_edit.py`, `sportorg/gui/dialogs/group_mass_edit.py`, `sportorg/gui/dialogs/settings.py`, `sportorg/gui/dialogs/dialog.py`, `configs/status_comments.txt`, `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po`
- Region: `sportorg/settings.py` (T4), `sportorg/models/memory.py` (T4), `sportorg/models/result/result_checker.py` (T4)

**Interfaces:**
- Produces: `settings.SETTINGS.NOVOSIVIRSK_ROGAINE_PAIRS: Dict`; `memory.PrintableValue`; result_checker rogaine scoring honoring `enabled`/`limit_num_controls`/`ignored_controls_by_course`/`pair_score_bonus`.

- [ ] **Step 1: Whole single-owner files**
```bash
git show dev-ank:sportorg/common/levenshtein.py > sportorg/common/levenshtein.py
git show dev-ank:tests/test_levenshtein.py > tests/test_levenshtein.py
git show dev-ank:sportorg/gui/dialogs/group_edit.py > sportorg/gui/dialogs/group_edit.py
git show dev-ank:sportorg/gui/dialogs/group_mass_edit.py > sportorg/gui/dialogs/group_mass_edit.py
git show dev-ank:sportorg/gui/dialogs/settings.py > sportorg/gui/dialogs/settings.py
git show dev-ank:sportorg/gui/dialogs/dialog.py > sportorg/gui/dialogs/dialog.py
git show dev-ank:configs/status_comments.txt > configs/status_comments.txt
git show dev-ank:sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po > sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po
```

- [ ] **Step 2: settings.py T4 region** — add only `NOVOSIVIRSK_ROGAINE_PAIRS` field (not the photo feature flag/path).

- [ ] **Step 3: memory.py T4 regions** — `PrintableValue`, `check` signature `course: Course = None`, `Race.find_course` group filter. No experimental blocks.

- [ ] **Step 4: result_checker.py T4 regions** — build by subtraction:
```bash
git show dev-ank:sportorg/models/result/result_checker.py > sportorg/models/result/result_checker.py
```
Then with `Edit`, delete (a) all 5 `NOVOSIBIRSK_VYBOR_PAIRS_V2 = False` blocks and (b) the `marked_route_check_penalty_laps` staticmethod. Result = imports + `is_any_course` change + real rogaine scoring only.

- [ ] **Step 5: Syntax check** settings.py, memory.py, result_checker.py.

- [ ] **Step 6: Green check** — `uv run poe test-fast` → exit 0 (includes `tests/test_levenshtein.py`).

- [ ] **Step 7: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(rogaine): configurable Novosibirsk vybor scoring"
```

---

## Task 5: T5 — import photo controls from CSV

**Files:**
- Whole: `sportorg/models/result/photo_controls.py` (new), `tests/test_photo_controls.py` (new)
- Region: `sportorg/settings.py` (T5), `sportorg/gui/dialogs/text_io.py` (T5 photo hunks), `sportorg/gui/main_window.py` (T5), `sportorg/gui/menu/actions.py` (T5), `sportorg/gui/menu/menu.py` (T5), `sportorg/modules/printing/printout_split.py` (T5)

**Interfaces:** Consumes `settings.FEATURE_ROGAINE_PHOTO_CONTROLS`. Produces `photo_controls.append_photo_controls`, `photo_controls.load_team_controls`, `photo_controls.is_photo_mark`.

- [ ] **Step 1: Whole new files**
```bash
git show dev-ank:sportorg/models/result/photo_controls.py > sportorg/models/result/photo_controls.py
git show dev-ank:tests/test_photo_controls.py > tests/test_photo_controls.py
```

- [ ] **Step 2: settings.py T5 region** — `FEATURE_ROGAINE_PHOTO_CONTROLS` const + `DEFAULT_FEATURES` entry + `rogaine_photo_controls_path` field. After this, settings.py **closes**: `git diff dev-ank -- sportorg/settings.py` → empty.

- [ ] **Step 3: Region edits** — apply T5 regions to `text_io.py` (photo/CSV hunks only), `main_window.py` (photo import + apply-on-read; NOT the HuichangClient reorder), `actions.py` (`import os`, `ResultSportident`/`photo_controls` imports, `UpdatePhotoControlsAction`), `menu.py` (photo menu item), `printout_split.py` (`import settings`, `is_photo_mark`, title-by-`<br>`, "ФОТО КП" block).

- [ ] **Step 4: Syntax check** every changed `.py`.

- [ ] **Step 5: Green check** — `uv run poe test-fast` → exit 0 (includes `tests/test_photo_controls.py`).

- [ ] **Step 6: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(rogaine): import photo controls from CSV"
```

---

## Task 6: T6 — multiday live send and online-CP status

**Files:**
- Whole: `sportorg/modules/live/live.py`, `sportorg/modules/live/orgeo.py`, `sportorg/modules/winorient/wdb.py`
- Region: `sportorg/gui/menu/actions.py` (`OnlineMultidaySendAll`), `sportorg/gui/menu/menu.py` (multiday item)

**Interfaces:** Produces `WinOrientBinary.get_wdb_status(status)`; `Orgeo.send_online_cp(chip, code, time, status=0)`.

- [ ] **Step 1: Whole files**
```bash
git show dev-ank:sportorg/modules/live/live.py > sportorg/modules/live/live.py
git show dev-ank:sportorg/modules/live/orgeo.py > sportorg/modules/live/orgeo.py
git show dev-ank:sportorg/modules/winorient/wdb.py > sportorg/modules/winorient/wdb.py
```

- [ ] **Step 2: Region edits** — `actions.py` add `OnlineMultidaySendAll`; `menu.py` add "Send multiday start list and results". After this, **actions.py closes**: `git diff dev-ank -- sportorg/gui/menu/actions.py` → empty.

- [ ] **Step 3: Syntax check** changed `.py`.

- [ ] **Step 4: Green check** — `uv run poe test-fast` → exit 0.

- [ ] **Step 5: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(live): multiday send and online-CP status"
```

---

## Task 7: T7 — WinOrient CSV import improvements

**Files:** Whole: `sportorg/modules/winorient/winorient.py`

- [ ] **Step 1: Take whole**
```bash
git show dev-ank:sportorg/modules/winorient/winorient.py > sportorg/modules/winorient/winorient.py
```
- [ ] **Step 2: Syntax check** winorient.py.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat(winorient): drop duplicate cards, parse в/к and лично on CSV import"
```

---

## Task 8: T8 — comma decimal separator in time parsing

**Files:**
- Whole: `sportorg/utils/time.py`
- Region: `sportorg/gui/dialogs/text_io.py` (time-rounding hunk)

- [ ] **Step 1: utils/time.py whole**
```bash
git show dev-ank:sportorg/utils/time.py > sportorg/utils/time.py
```
- [ ] **Step 2: text_io.py T8 region** — apply the remaining (time-rounding) hunk. After this, **text_io.py closes**: `git diff dev-ank -- sportorg/gui/dialogs/text_io.py` → empty.
- [ ] **Step 3: Syntax check** both `.py`.
- [ ] **Step 4: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 5: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "fix(time): accept comma as decimal separator in hh:mm:ss parsing"
```

---

## Task 9: T9 — marked route penalty-lap check by station

**Files:**
- Region: `sportorg/models/result/result_checker.py` (`marked_route_check_penalty_laps`), `tests/test_penalty_checking.py` (T9 hunks)

**Interfaces:** Produces `ResultChecker.marked_route_check_penalty_laps(result)`.

- [ ] **Step 1: Add the staticmethod** — re-insert `marked_route_check_penalty_laps` into `result_checker.py` (removed in Task 4) from netdiff.patch.
- [ ] **Step 2: test_penalty_checking.py T9 region** — apply the marked-route test additions (and its added imports). If a hunk tests rogaine pair scoring instead, it belonged in T4; verify by reading the hunk body.
- [ ] **Step 3: Syntax check** result_checker.py, test_penalty_checking.py. After this, **test_penalty_checking.py closes**: `git diff dev-ank -- tests/test_penalty_checking.py` → empty.
- [ ] **Step 4: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 5: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "feat: marked route penalty-lap check by station code"
```

---

## Task E1: TE1 — Nizhny Novgorod relay finish-by-station (experimental)

**Files:** Region: `sportorg/models/memory.py` (`get_finish_time` `nizhni_novgorod_relay` block)

- [ ] **Step 1:** Insert the `nizhni_novgorod_relay = False` block into `ResultSportident.get_finish_time` from netdiff.patch.
- [ ] **Step 2: Syntax check** memory.py.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0 (block is inert).
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(experimental): Nizhny Novgorod relay finish-by-station"
```

---

## Task E2: TE2 — Novosibirsk vybor paired controls v1 (experimental)

**Files:** Region: `sportorg/models/memory.py` (`check`: `NOVOSIBIRSK_VYBOR_PAIRS` setup + recognition block + `if False and ...` block)

- [ ] **Step 1:** Insert all three TE2 regions into `ResultSportident.check` from netdiff.patch (setup block near top, recognition block inside the unique-control loop, and the `if False and NOVOSIBIRSK_VYBOR_PAIRS:` block).
- [ ] **Step 2: Syntax check** memory.py.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(experimental): Novosibirsk vybor paired controls v1"
```

---

## Task E3: TE3 — Novosibirsk vybor classic (experimental)

**Files:** Region: `sportorg/models/memory.py` (`check`: `NOVOSIBIRSK_VYBOR_CLASSIC` block)

- [ ] **Step 1:** Insert the `NOVOSIBIRSK_VYBOR_CLASSIC = False` block into `check` from netdiff.patch.
- [ ] **Step 2: Syntax check** memory.py.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(experimental): Novosibirsk vybor classic"
```

---

## Task E4: TE4 — Novosibirsk vybor paired controls v2 (experimental, 5×)

**Files:** Region: `sportorg/models/result/result_checker.py` (`NOVOSIBIRSK_VYBOR_PAIRS_V2` block ×5)

- [ ] **Step 1:** Re-insert all **5 verbatim copies** of the `NOVOSIBIRSK_VYBOR_PAIRS_V2 = False` block (removed in Task 4) into the rogaine scoring function, at the exact positions in dev-ank (between the real head block and `user_array = []`). Source: `git show dev-ank:sportorg/models/result/result_checker.py`.
- [ ] **Step 2: Per-file equality (closes result_checker.py):** `git diff dev-ank -- sportorg/models/result/result_checker.py` → empty.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(experimental): Novosibirsk vybor paired controls v2"
```

---

## Task E5: TE5 — Tomsk marked route (experimental)

**Files:** Region: `sportorg/models/memory.py` (`check`: `tomsk_marked_route` commented DSQ block), `sportorg/modules/printing/printout_split.py` (`tomsk_marked_route` skip-printing block)

- [ ] **Step 1:** Insert the TE5 region into `memory.py` `check`, and the `tomsk_marked_route = False` skip block into `printout_split.py` from netdiff.patch.
- [ ] **Step 2: Syntax check** both `.py`.
- [ ] **Step 3: Green check** — `uv run poe test-fast` → exit 0.
- [ ] **Step 4: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(experimental): Tomsk marked route"
```

---

## Task D: TD — contributing notes (docs)

**Files:** Whole: `doc/dev-ank-contributing.md` (new)

- [ ] **Step 1:**
```bash
git show dev-ank:doc/dev-ank-contributing.md > doc/dev-ank-contributing.md
```
- [ ] **Step 2: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "docs: add dev-ank contributing notes"
```

---

## Task M: TM — cosmetic leftovers + final verification

**Files:** Region: `sportorg/models/memory.py` (`get_start_time` `-> OTime`), `sportorg/gui/main_window.py` (HuichangClient import reorder), `sportorg/gui/menu/menu.py` (duplicate `"shortcut": "Ctrl+E"`), `sportorg/modules/printing/printout_split.py` (Xprinter comment)

- [ ] **Step 1: Apply the four cosmetic regions** from netdiff.patch.

- [ ] **Step 2: Per-file equality (closing files)** — each must be empty:
```bash
git diff dev-ank -- sportorg/models/memory.py
git diff dev-ank -- sportorg/gui/main_window.py
git diff dev-ank -- sportorg/gui/menu/menu.py
git diff dev-ank -- sportorg/modules/printing/printout_split.py
```

- [ ] **Step 3: Commit**
```bash
git add <files listed in this task's **Files** block>
git commit -m "chore(misc): cosmetic leftovers to match dev-ank"
```

- [ ] **Step 4: FINAL tree equality (acceptance)**
Run: `git diff ank/dev dev-ank`
Expected: **empty** (byte-for-byte match, including the 5× E4).

- [ ] **Step 5: Full test gate**
Run: `uv run poe test`
Expected: exit 0, coverage ≥42%.

- [ ] **Step 6: Lint gate**
Run: `uv run poe lint`
Expected: exit 0 (matches dev-ank's lint status).

- [ ] **Step 7: Review the shape**
```bash
git log --oneline master..ank/dev      # expect 16 commits, T1..TM in order
```

- [ ] **Step 8: Worktree disposition**
The `ank/dev` branch now exists in the shared repo. Leave the worktree in place for review, or remove it once satisfied (the branch persists):
```bash
cd C:/Users/ank/Documents/Prog/SportOrg/pysport      # back to main checkout (openspec-base)
git worktree remove C:/Users/ank/Documents/Prog/SportOrg/pysport-ankdev   # optional; branch ank/dev is kept
```

---

## Self-review notes

- **Spec coverage:** every spec commit (T1–T9, E1–E5, D, M) has a task; all 34 net-diff files are assigned in the shared-file map or as whole-file takes.
- **Tree fidelity:** guaranteed by per-file equality at each closing commit + the final `git diff ank/dev dev-ank` empty.
- **Greenness:** experimental/docs/misc commits are inert or additive; `poe test-fast` after each. Coverage gate only at the tip (`poe test`).
- **Known soft spot:** the exact text_io.py (#5/#8) and test_penalty_checking.py (#4/#9) hunk attribution may need a judgment call while reading hunk bodies; final equality still holds regardless of minor mis-attribution between those paired commits.
