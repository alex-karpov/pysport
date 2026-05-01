## ADDED Requirements

### Requirement: short_title field on RaceData
`RaceData` SHALL have a `short_title: str` attribute initialized to `""`.
It SHALL be included in `to_dict()` output and restored in `update_data()`.
When loading a JSON file that lacks the key, the system SHALL default to `""` without error.

#### Scenario: New race has empty short_title
- **WHEN** a new `RaceData` object is created
- **THEN** `short_title` equals `""`

#### Scenario: Save and reload round-trip
- **WHEN** `short_title` is set to a non-empty string and the file is saved then reopened
- **THEN** the loaded `short_title` equals the saved value

#### Scenario: Loading old file without short_title key
- **WHEN** a JSON file is loaded that has no `"short_title"` key in the data section
- **THEN** `short_title` is set to `""` and no exception is raised

### Requirement: Event Properties dialog exposes short_title
The Event Properties dialog SHALL display a `short_title` input field after the Sub title field.
The field SHALL have a placeholder text equal to the event's start date formatted as `YYYY.MM.DD`.
The field SHALL be pre-populated with the current `short_title` value when the dialog opens.
On OK, the entered value SHALL be saved to `RaceData.short_title` (empty string if left blank).

#### Scenario: Dialog opens with existing short_title
- **WHEN** the dialog opens and `short_title` is `"Day 1"`
- **THEN** the input field shows `"Day 1"`

#### Scenario: Placeholder shows start date
- **WHEN** the dialog opens and `short_title` is `""` and start date is 2024-06-15
- **THEN** the placeholder text shows `"2024.06.15"`

#### Scenario: Saving empty field stores empty string
- **WHEN** the user clears the short_title field and clicks OK
- **THEN** `RaceData.short_title` is `""`

### Requirement: Window title uses short_title
The main window title SHALL follow the format:
`<label> [<datetime>] [<full_path>] — SportOrg <version>`

Where `<label>` is `short_title` if non-empty, otherwise `os.path.basename(file)` (filename with extension).
When no file is open, the title SHALL be `SportOrg <version>` (unchanged).
The separator before the app name SHALL be ` — ` (space + em dash + space).

#### Scenario: short_title set, file open
- **WHEN** `short_title` is `"Sprint Q"` and a file `/path/race.json` is open
- **THEN** window title is `"Sprint Q [<datetime>] [/path/race.json] — SportOrg v..."`

#### Scenario: short_title empty, file open
- **WHEN** `short_title` is `""` and file `/path/race.json` is open
- **THEN** window title is `"race.json [<datetime>] [/path/race.json] — SportOrg v..."`

#### Scenario: No file open
- **WHEN** no file is open
- **THEN** window title is `"SportOrg <version>"` (no change from current behavior)

### Requirement: Race selector lists show short_title
In the Settings dialog and SportOrg Import dialog, each race in the multi-day selector list SHALL display `short_title` when it is non-empty. When `short_title` is empty, the list SHALL display `str(get_start_datetime())` as before.

#### Scenario: Race with short_title in selector
- **WHEN** `short_title` is `"Day 2"` and the multi-day race list is populated
- **THEN** the list item shows `"Day 2"`

#### Scenario: Race without short_title in selector
- **WHEN** `short_title` is `""` and the multi-day race list is populated
- **THEN** the list item shows the start datetime string

### Requirement: Translations for short_title UI strings
The strings `"Short title"` and its tooltip `"Brief operator-only label. Shown in the window title and event list, not printed in protocols."` SHALL have entries in both `ru_RU` and `en_US` `.po` catalogs. The `.mo` files SHALL be regenerated after the `.po` files are updated.

#### Scenario: ru_RU translation applied
- **WHEN** the application locale is `ru_RU` and the Event Properties dialog opens
- **THEN** the short_title field label shows `"Короткое название"`

#### Scenario: en_US translation applied
- **WHEN** the application locale is `en_US` and the Event Properties dialog opens
- **THEN** the short_title field label shows `"Short title"`
