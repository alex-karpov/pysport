## ADDED Requirements

### Requirement: Single feature flag for photo controls
The system SHALL define `FEATURE_ROGAINE_PHOTO_CONTROLS = "rogaine_photo_controls"` in `sportorg/settings.py`, registered in `DEFAULT_FEATURES` with a default value of `False`. All photo-control behavior (live readout merge, bulk menu action, split-printout rendering) SHALL be gated by `settings.is_feature_enabled(FEATURE_ROGAINE_PHOTO_CONTROLS)`. No inline `ROGAINE_PHOTO_CONTROLS` boolean SHALL remain in the codebase.

#### Scenario: Disabled by default
- **WHEN** a fresh settings object is created
- **THEN** `is_feature_enabled(FEATURE_ROGAINE_PHOTO_CONTROLS)` returns `False`

#### Scenario: Menu item hidden when disabled
- **WHEN** the feature is disabled
- **THEN** the "Update photo controls from CSV" menu item is not shown

#### Scenario: Settings dialog exposes the toggle
- **WHEN** the Settings dialog opens
- **THEN** a checkbox labelled "Rogaine photo controls" reflects and can change the feature state

### Requirement: CSV path configured in settings
The system SHALL persist the photo-controls CSV path in `settings.SETTINGS.rogaine_photo_controls_path` (default `""`). The Settings dialog SHALL provide an input — with a file-browse button — to view and change this path, placed near the photo-controls feature checkbox. Both the live readout and the bulk menu action SHALL read the CSV from this single configured path and SHALL NOT prompt for a file at use time.

#### Scenario: Path saved from settings dialog
- **WHEN** the operator sets a path in the Settings dialog and confirms
- **THEN** `settings.SETTINGS.rogaine_photo_controls_path` equals that path and persists across save/reload

#### Scenario: Single source for both paths
- **WHEN** the path is configured in settings
- **THEN** both live readout and the bulk action use it without any file prompt

### Requirement: Shared photo-controls module
The system SHALL provide `sportorg/models/result/photo_controls.py` with:
- `load_team_controls(csv_path)` returning a mapping `{team_bib: [code, ...]}` parsed from a `;`-delimited CSV where column index 1 is the team bib and column index 2 is the control code;
- `append_photo_controls(result, team_controls)` that merges the team's photo controls into `result.splits` and returns the number of marks added.

The team bib for a result SHALL be computed as `result.person.bib // 10`. A result whose person has no bib SHALL be skipped and a warning logged; no marks SHALL be added for it.

Each added photo mark SHALL be a `Split` with `code` set to the CSV control code and `time` set to `result.get_start_time()`, prepended to existing splits.

#### Scenario: Parse maps team bib to codes
- **WHEN** the CSV contains rows `x;12;31` and `x;12;32`
- **THEN** `load_team_controls` returns `{12: ["31", "32"]}`

#### Scenario: Team bib derived from bib
- **WHEN** a result's person has bib `123` and the mapping contains key `12`
- **THEN** that team's codes are the ones applied to the result

#### Scenario: Result without bib is skipped
- **WHEN** a result's person has no bib (or no person)
- **THEN** `append_photo_controls` adds nothing for it and logs a warning

### Requirement: Idempotent merge of photo controls
`append_photo_controls` SHALL add a photo mark for control code `C` only when `result.splits` does not already contain a split `s` satisfying `s.code == C` AND `abs(s.time - result.get_start_time()) <= 1 second`. Running the merge repeatedly over a result that already contains its photo marks SHALL add nothing. A real chip punch of the same control (with a time far from the start time) SHALL NOT suppress the photo mark.

#### Scenario: No duplication on re-run
- **WHEN** `append_photo_controls` is applied twice to the same result with the same mapping
- **THEN** the second call adds `0` marks and the split set is unchanged

#### Scenario: Real punch does not suppress photo mark
- **WHEN** a result already contains a real punch for code `C` with a mid-race time far from the start time
- **AND** the team's photo controls include code `C`
- **THEN** a photo mark for `C` at the start time is still added

#### Scenario: Existing photo mark suppresses re-add
- **WHEN** a result already contains a split for code `C` whose time equals the start time
- **AND** the team's photo controls include code `C`
- **THEN** no additional mark for `C` is added

### Requirement: Live readout applies photo controls from stored path
When the feature is enabled, `add_sportident_result_from_sireader` SHALL load photo controls from `settings.SETTINGS.rogaine_photo_controls_path` and apply them to the just-read result via `append_photo_controls`, then call `recalculate_results(recheck_results=True, group=group)`. When the feature is disabled, no photo controls SHALL be applied and `recalculate_results(recheck_results=False, group=group)` SHALL be called (current behavior). When the stored path is empty or unreadable, the readout SHALL proceed without photo controls and SHALL NOT raise.

#### Scenario: Feature enabled, path set
- **WHEN** a chip is read, the feature is enabled, and the stored CSV path is valid
- **THEN** the team's missing photo controls are merged into the result before recalculation

#### Scenario: Feature enabled, path empty
- **WHEN** a chip is read, the feature is enabled, and the stored CSV path is empty
- **THEN** the result is processed normally with no photo controls and no error

#### Scenario: Feature disabled
- **WHEN** a chip is read and the feature is disabled
- **THEN** no photo controls are applied and `recalculate_results` is called with `recheck_results=False`

### Requirement: Bulk update menu action
The system SHALL provide a Results menu item "Update photo controls from CSV", gated by the feature flag. Activating it SHALL load the CSV at `settings.SETTINGS.rogaine_photo_controls_path` without prompting, parse it once via `load_team_controls`, apply `append_photo_controls` to every `ResultSportident` in `race().results`, then call `recalculate_results()` and refresh the view. When the configured path is empty or unreadable, the action SHALL inform the operator and make no changes.

#### Scenario: Apply to all read chips
- **WHEN** the action runs and the configured CSV path is valid, over a race containing several read chips
- **THEN** each chip receives its team's missing photo controls and results are recalculated

#### Scenario: Empty path
- **WHEN** the action runs and `settings.SETTINGS.rogaine_photo_controls_path` is empty or unreadable
- **THEN** no results are modified and the operator is informed

### Requirement: Split printout renders photo controls under the feature flag
The split printout SHALL render a split as a `ФОТО КП` line (instead of the normal split line) when the feature is enabled and the split's time equals the result's start time, using `settings.is_feature_enabled(FEATURE_ROGAINE_PHOTO_CONTROLS)` rather than an inline boolean.

#### Scenario: Photo mark rendered specially when enabled
- **WHEN** the feature is enabled and a split's time equals the start time
- **THEN** the split prints as a `ФОТО КП` line

#### Scenario: Normal rendering when disabled
- **WHEN** the feature is disabled
- **THEN** all splits print with the normal split line format

### Requirement: Translations for photo-control UI strings
The strings "Update photo controls from CSV" (menu item) and "Rogaine photo controls" (settings checkbox) SHALL have entries in both `ru_RU` and `en_US` `.po` catalogs, and the `.mo` files SHALL be regenerated.

#### Scenario: ru_RU strings applied
- **WHEN** the locale is `ru_RU`
- **THEN** the menu item and checkbox show their Russian translations

#### Scenario: en_US strings applied
- **WHEN** the locale is `en_US`
- **THEN** the menu item and checkbox show the English source strings
