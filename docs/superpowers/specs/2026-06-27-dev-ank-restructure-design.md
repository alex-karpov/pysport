# Restructuring the dev-ank branch → ank/dev

Date: 2026-06-27

## Goal

The `dev-ank` branch holds several features smeared across 27 messy commits
(markers `=== dev-ank changes ===`, `=== rebase to master ===`, duplicate
`NOVOSIBIRSK_VYBOR_PAIRS_V2` and "Перенесён в настройки" commits). We need to build
a new branch `ank/dev` where **each feature is a single clean commit**.

## Key facts

- `master` == `origin/master` == `upstream/master` == merge-base with `dev-ank`
  (`c11c36d9`). So `ank/dev` is built **from `master`**.
- The source of truth is the **net diff** `git diff master..dev-ank` (34 files,
  +2578/−249), **not** the commit history.

## Decisions (agreed with the user)

1. **Hybrid scope.** Clean per-feature commits + preserve everything in `dev-ank`,
   so that `git diff ank/dev dev-ank` is **empty**.
2. **Each experimental feature under `= False` gets its own commit** (not one
   catch-all).
3. **Relay: logic and display are two separate commits.**
4. **WinOrient import and the time fix are separate commits.**
5. **`marked_route_check_penalty_laps` is its own commit.**
6. **Every commit is green** (imports independently and passes tests).
7. **E4 (`NOVOSIBIRSK_VYBOR_PAIRS_V2`) is reproduced 5× verbatim** — in `dev-ank`
   the block was accidentally copy-pasted 5 times; we keep it as-is for a
   byte-for-byte tree match.

## Build strategy

Do not try to clean up the `dev-ank` history (hopeless). Reconstruct from the net diff:

1. `git switch -c ank/dev master`.
2. For each commit:
   - **new files** are taken whole: `git show dev-ank:<path> > <path>`;
   - **shared files** are split at the hunk level (via targeted `git apply` patches
     or manual editing), including only the changes that belong to that commit.
3. Commit using Conventional Commits messages (see the list).

Shared files that must be split by hunks:
`memory.py`, `text_io.py`, `gui/menu/actions.py`, `gui/menu/menu.py`,
`settings.py`, `result_checker.py`, `printing/printout_split.py`,
`gui/main_window.py`.

## Commit plan (order = order of application)

### Real features

1. **`feat(relay): place relay teams as in all-Russian competitions`**
   - `result_calculation.py` (sort_relay_all_russian_competition, handling of
     out-of-competition and mixed teams)
   - `memory.py`: `Group.is_all_russian_competition` (+to_dict/update); `RelayTeam`
     (`__lt__`, `get_is_team_placed(place_out_of_competition)`, `get_is_out_of_competition`, `get_is_mixed_team`)
   - `tests/test_relay_results.py`
   - `changelog.md`, `changelog_ru.md` (#495)

2. **`feat(results): relay bib format 15.1 and split display`**
   - `data/templates/script.js.html` (`to_relay_bib`, `align_right`, `toMMSS`,
     client-side sorting removed, Qualification)
   - `data/templates/split/1_сплиты_с_лидерами_на_перегонах.html` (new)
   - `memory.py`: `Race.to_dict` — server-side group sorting matching the Groups tab

3. **`feat(logging): daily rotating log files`**
   - `sportorg/logging.py` (new: `DailyFileHandler`, `make_log_filename`)
   - `config.py` (LOG_CONFIG → DailyFileHandler)
   - `modules/sportident/backup.py` (uses `make_log_filename`)

4. **`feat(rogaine): configurable Novosibirsk vybor scoring`**
   - `common/levenshtein.py` (new) + `tests/test_levenshtein.py`
   - `result_checker.py`: configurable `NOVOSIBIRSK_VYBOR` block
     (`SETTINGS.NOVOSIVIRSK_ROGAINE_PAIRS`: pairs/bonus/ignored/limit) + scoring-loop
     changes; `is_any_course` → `result.check(course)`. **Excludes** the dead
     `NOVOSIBIRSK_VYBOR_PAIRS_V2` and **excludes** `marked_route_check_penalty_laps`.
   - `settings.py`: `NOVOSIVIRSK_ROGAINE_PAIRS`
   - `memory.py`: `PrintableValue`, `Race.find_course` (filter by group name)
   - `gui/dialogs/group_edit.py`, `group_mass_edit.py`, `dialogs/settings.py` (FunctionsTab), `dialog.py` (tooltip)
   - `configs/status_comments.txt`, `data/languages/ru_RU/.../sportorg.po`

5. **`feat(rogaine): import photo controls from CSV`**
   - `models/result/photo_controls.py` (new) + `tests/test_photo_controls.py`
   - `settings.py`: `FEATURE_ROGAINE_PHOTO_CONTROLS` + `rogaine_photo_controls_path`
   - `gui/dialogs/text_io.py` (CSV photo-controls import)
   - `gui/main_window.py` (apply on read-out) — **without** the HuichangClient import reorder
   - `gui/menu/actions.py` (`UpdatePhotoControlsAction`), `gui/menu/menu.py` (menu item)
   - `printing/printout_split.py` (`is_photo_mark`, "ФОТО КП")

6. **`feat(live): multiday send and online-CP status`**
   - `modules/live/live.py` (live_enabled/is_results gating), `modules/live/orgeo.py` (online-CP status)
   - `modules/winorient/wdb.py` (`get_wdb_status`)
   - `gui/menu/actions.py` (`OnlineMultidaySendAll`), `gui/menu/menu.py`

7. **`feat(winorient): drop duplicate cards, parse в/к and лично on CSV import`**
   - `modules/winorient/winorient.py`

8. **`fix(time): accept comma as decimal separator in hh:mm:ss parsing`**
   - `utils/time.py`; `gui/dialogs/text_io.py` (rounding part)

9. **`feat: marked route penalty-lap check by station code`**
   - `result_checker.py`: `marked_route_check_penalty_laps` (settings
     `marked_route_if_station_check`, `marked_route_penalty_lap_station_code`, status "пп4.6.12.7")
   - `tests/test_penalty_checking.py` (the related hunks)

### Experimental features (dead `= False`, inert → green)

- **E1 `chore(experimental): Nizhny Novgorod relay finish-by-station`** — `memory.py` `get_finish_time`
- **E2 `chore(experimental): Novosibirsk vybor paired controls v1`** — `memory.py` `check`
  (`NOVOSIBIRSK_VYBOR_PAIRS` + the `if False and ...` variant)
- **E3 `chore(experimental): Novosibirsk vybor classic`** — `memory.py` `check` (`NOVOSIBIRSK_VYBOR_CLASSIC`)
- **E4 `chore(experimental): Novosibirsk vybor paired controls v2`** — `result_checker.py`
  (`NOVOSIBIRSK_VYBOR_PAIRS_V2`, **5 verbatim copies** as in dev-ank)
- **E5 `chore(experimental): Tomsk marked route`** — `memory.py` `check` (commented-out DSQ) + `printout_split.py` (do not print correct controls)

### Docs and noise (for the tree match)

- **D `docs: add dev-ank contributing notes`** — `doc/dev-ank-contributing.md`
- **M `chore(misc): cosmetic leftovers to match dev-ank`** — HuichangClient import
  reorder in `main_window.py`; duplicate `"shortcut": "Ctrl+E"` in `menu.py`;
  `Result.get_start_time` type hint; Xprinter comment in `printout_split.py`;
  any remaining cosmetic hunks.

Total: **16 commits** (9 real + 5 experimental + docs + misc).

## Verification and acceptance criteria

- **Tip tree == dev-ank**: `git diff ank/dev dev-ank` is empty (including the 5× E4).
- **Full test suite** `uv run poe test` green at the tip (coverage threshold 42%).
- **Every commit green**: intermediate commits run `uv run poe test-fast` (no
  coverage threshold), the tip runs the full `uv run poe test`.
- `uv run poe lint` green at the tip.

## Risks

- **42% coverage threshold on intermediate commits.** Dead code lowers coverage;
  real features add tests and compensate. Resolution: run `test-fast` (no threshold)
  intermediately, full `test` at the tip.
- **Hunk-level splitting of shared files** is the bulk of the manual work; mitigated
  by the "tree == dev-ank" criterion, which catches any stitching mistake.
- **Splitting `tests/test_penalty_checking.py`** between #4 and #9 to be finalized
  during the planning stage.

## Out of scope

- Do not touch `dev-ank`, `master`, or other branches.
- Do not edit or "improve" the feature contents (ank/dev must mirror dev-ank).
- Do not push or open a PR without a separate request.
