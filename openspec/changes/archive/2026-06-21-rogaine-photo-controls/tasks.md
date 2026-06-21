## 1. Settings

- [x] 1.1 Add `FEATURE_ROGAINE_PHOTO_CONTROLS = "rogaine_photo_controls"` to `sportorg/settings.py` and register it in `DEFAULT_FEATURES` with value `False`
- [x] 1.2 Add `rogaine_photo_controls_path: str = ""` field to the `Settings` dataclass

## 2. Shared module

- [x] 2.1 Create `sportorg/models/result/photo_controls.py`
- [x] 2.2 Implement `load_team_controls(csv_path: str) -> Dict[int, List[str]]` (`;`-delimited; key = `int(row[1])`, code = `row[2]`)
- [x] 2.3 Implement `append_photo_controls(result: ResultSportident, team_controls: Dict[int, List[str]]) -> int`: compute `team_bib = result.person.bib // 10`, skip+log if no bib; for each team code build a `Split(code, time=start_time)`; apply dedup rule `s.code == C AND abs(s.time - start_time) <= 1s` (real punches with mid-race times do not suppress); prepend missing marks; return count added

## 3. Live readout

- [x] 3.1 In `add_sportident_result_from_sireader` (`sportorg/gui/main_window.py`) replace inline `ROGAINE_PHOTO_CONTROLS` with `feature = settings.is_feature_enabled(settings.FEATURE_ROGAINE_PHOTO_CONTROLS)`
- [x] 3.2 When `feature` and `settings.SETTINGS.rogaine_photo_controls_path` is set/readable: `append_photo_controls(result, load_team_controls(path))`; guard against missing/unreadable file (no raise)
- [x] 3.3 Keep `recalculate_results(recheck_results=feature, group=group)`
- [x] 3.4 Remove the old `MainWindow.append_photo_controls` method and its hard-coded path

## 4. Bulk menu action

- [x] 4.1 Add `UpdatePhotoControlsAction` in `sportorg/gui/menu/actions.py`: read `settings.SETTINGS.rogaine_photo_controls_path` (no file dialog); if empty/unreadable inform operator and return; `load_team_controls` once; loop `race().results` applying `append_photo_controls`; `recalculate_results()`; `self.app.refresh()`
- [x] 4.2 Add the menu item under "Results" in `sportorg/gui/menu/menu.py` with `"feature": settings.FEATURE_ROGAINE_PHOTO_CONTROLS` and `"action": "UpdatePhotoControlsAction"`

## 5. Split printout

- [x] 5.1 In `sportorg/modules/printing/printout_split.py` replace inline `ROGAINE_PHOTO_CONTROLS = False` with `settings.is_feature_enabled(settings.FEATURE_ROGAINE_PHOTO_CONTROLS)`

## 6. Settings dialog

- [x] 6.1 Add `(settings.FEATURE_ROGAINE_PHOTO_CONTROLS, "Rogaine photo controls")` to the feature checkbox tuple in `sportorg/gui/dialogs/settings.py`
- [x] 6.2 Add a CSV path input + Browse button near that checkbox, bound to `settings.SETTINGS.rogaine_photo_controls_path` (load on open, save on apply)

## 7. Translations

- [x] 7.1 Add `ru_RU` entries: "Update photo controls from CSV" → "Обновить фото-КП из CSV"; "Rogaine photo controls" → "Фото-КП рогейна"
- [~] 7.2 Skipped: en_US falls back to msgid via gettext; no identity entries added (per user)
- [x] 7.3 Run `uv run poe generate-mo`

## 8. Tests

- [x] 8.1 Unit-test `load_team_controls` parsing and `append_photo_controls` dedup (re-run adds 0; real punch does not suppress; existing photo mark suppresses; no-bib skipped)
