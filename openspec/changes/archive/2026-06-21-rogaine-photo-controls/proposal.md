## Why

In rogaine events some controls are confirmed by photo instead of an SI punch. These "photo controls" live in an external CSV (one row per team+control) and must be merged into each team's read chip as extra splits. Today this works only for chips read live, the feature is toggled by two out-of-sync inline `ROGAINE_PHOTO_CONTROLS` booleans, and the CSV path is hard-coded in the source. There is no way to apply photo controls to chips that were already read (before the CSV was ready, or after the CSV was updated), and re-applying would blindly duplicate marks.

## What Changes

- New feature flag `settings.FEATURE_ROGAINE_PHOTO_CONTROLS` (default `False`) — single source of truth replacing both inline `ROGAINE_PHOTO_CONTROLS` locals (live readout + split printout). Exposed as a checkbox in the Settings dialog.
- New persisted setting `rogaine_photo_controls_path` holding the CSV path, configured in the Settings dialog next to the feature checkbox. Both the live readout and the bulk menu action read the CSV from this single path — no per-use file prompt.
- New shared module `sportorg/models/result/photo_controls.py` with reusable `load_team_controls(csv_path)` and `append_photo_controls(result, team_controls)`; the live readout and the new menu action both use it.
- New menu item **Results → "Update photo controls from CSV"** (gated by the feature flag): loads the CSV at the configured path, parses it once, and applies photo controls to **all** read chips, then rechecks and refreshes.
- Idempotent merge: a photo control is added only if the chip does not already have a photo mark for that code near the start time (dedup rule below), so re-running over chips that already contain photo marks does not duplicate them. A real chip punch of the same control does NOT suppress the photo mark.
- New `ru_RU` / `en_US` translations for the menu item and the feature checkbox label.

## Capabilities

### New Capabilities
- `rogaine-photo-controls`: merge externally-supplied photo controls into read chips, both live and in bulk, gated by a single feature flag

### Modified Capabilities

## Impact

- `sportorg/settings.py` — feature constant + `DEFAULT_FEATURES` entry + `rogaine_photo_controls_path` field
- `sportorg/models/result/photo_controls.py` — new shared module (`load_team_controls`, `append_photo_controls`)
- `sportorg/gui/main_window.py` — remove inline flag/hard-coded path; live readout uses feature flag, stored path, and the shared function
- `sportorg/gui/menu/menu.py` — new Results menu item with `feature` gate
- `sportorg/gui/menu/actions.py` — new `UpdatePhotoControlsAction`
- `sportorg/modules/printing/printout_split.py` — replace inline `ROGAINE_PHOTO_CONTROLS = False` with feature-flag check
- `sportorg/gui/dialogs/settings.py` — add feature to the checkbox tuple + CSV path input (browse) near it, bound to `rogaine_photo_controls_path`
- `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po` + `.mo`
- `sportorg/data/languages/en_US/LC_MESSAGES/sportorg.po` + `.mo`
