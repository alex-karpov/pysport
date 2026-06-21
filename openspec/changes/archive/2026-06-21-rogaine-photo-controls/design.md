## Context

`MainWindow.append_photo_controls()` currently:
- hard-codes a per-event CSV path,
- computes `team_bib = bib // 10`,
- reads a `;`-delimited CSV with columns `[_, team_bib, code]`,
- builds `Split` objects with `code = row[2]` and `time = result.get_start_time()`,
- **prepends** them to `result.splits`.

It is called from `add_sportident_result_from_sireader()` gated by an inline `ROGAINE_PHOTO_CONTROLS = True`, and `recalculate_results(recheck_results=ROGAINE_PHOTO_CONTROLS, group=group)` is called afterward. A second, out-of-sync inline `ROGAINE_PHOTO_CONTROLS = False` in `printout_split.py` controls rendering of photo marks (splits at start time) as `ФОТО КП`.

## Goals

- One feature flag, reused everywhere.
- One reusable merge function, used by both live readout and a new bulk menu action.
- Re-running the merge does not duplicate already-loaded photo marks.

## Decisions

### Feature flag location
Reuse the existing feature-flag infrastructure: `settings.FEATURE_ROGAINE_PHOTO_CONTROLS = "rogaine_photo_controls"`, added to `DEFAULT_FEATURES` with default `False`. This gives, for free: menu gating via the `"feature"` key, a Settings-dialog checkbox (by extending the existing `(feature, title)` tuple), and removes the True/False drift between the two call sites.

### CSV path (single configured source)
The CSV path is configured once in the Settings dialog (a text input + Browse button placed next to the feature checkbox) and persisted in `settings.SETTINGS.rogaine_photo_controls_path`. Neither the live readout nor the bulk menu action prompts for a file — both read this one path:
- Live readout: if the path is empty/unreadable it skips silently (feature inert until a path is set).
- Bulk action: if the path is empty/unreadable it informs the operator and makes no changes.

### Shared module
`sportorg/models/result/photo_controls.py` (next to `result_tools.py`):

```
load_team_controls(csv_path: str) -> Dict[int, List[str]]
    # parse once: {team_bib: [code, ...]}; team_bib = int(row[1]); code = row[2]

append_photo_controls(result: ResultSportident, team_controls: Dict[int, List[str]]) -> int
    # returns number of marks added; skips results without bib (logs warning)
```

`append_photo_controls` is pure logic over a Result + a pre-parsed mapping, so the bulk path parses the CSV exactly once and reuses it across all results, while the live path parses (cheaply) per chip.

### Dedup rule (idempotent merge)
The candidate photo mark has `code = C`, `time = start_time`. It is **skipped** when `result.splits` already contains a split `s` such that:

```
s.code == C  AND  |s.time - start_time| <= 1 second
```

Consequence: only previously-loaded photo marks (which sit at the start time, the `±1s` absorbing rounding) suppress re-adding. A real SI punch of the same control, with a real mid-race time, does **not** suppress the photo mark — so a control may exist both as a punch and as a photo mark. This is intentional: photo marks must always be shown, even when the control was also punched.

`team_bib = bib // 10`. Results without a bib are skipped with a logged warning (no `team_bib = 0` fallback).

### Recheck behavior
Preserve current semantics: the live path calls `recalculate_results(recheck_results=<feature>, group=group)` — `recheck_results` follows the feature flag (matches the pre-rogaine default of `False` when off, and `True` when photo controls were appended). The bulk action calls `recalculate_results()` (full recheck) once after processing all results.

### Ordering
Missing photo marks are prepended (as today). After recheck, `course_index`/`leg_time` are recomputed.

## Risks / Trade-offs

- Photo marks remain identified only by `time == start_time` (no explicit field on `Split`). The dedup and the printout rendering both rely on this convention; documented here so future changes keep it consistent.
- A control both punched and photographed appears twice — accepted, per the dedup rule.
