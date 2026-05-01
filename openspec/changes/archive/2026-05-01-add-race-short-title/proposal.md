## Why

Operators managing multi-event or multi-day competitions need a short, private label to distinguish races at a glance — the full event name is too long for a window title, and the start datetime is not descriptive enough. `short_title` gives operators a concise, human-readable identifier that appears in the UI without polluting printed protocols.

## What Changes

- New `short_title` field on `RaceData` (persisted in JSON, empty string by default)
- Event Properties dialog: new input field with date-based placeholder, positioned after Sub title
- Window title format changed from `<datetime> [<path>] - SportOrg` to `<short_title|filename> [<datetime>] [<path>] — SportOrg` (em dash separator)
- Multi-day race selector lists (Settings dialog, SportOrg Import dialog) show `short_title` when non-empty, fall back to start datetime
- New `ru_RU` and `en_US` translations for "Short title" and its tooltip

## Capabilities

### New Capabilities
- `race-short-title`: Short operator-only label stored on RaceData, shown in window title and race selector lists, not printed in protocols

### Modified Capabilities

## Impact

- `sportorg/models/memory.py` — `RaceData` class
- `sportorg/modules/backup/json.py` — backward-compatible load via `.get()`
- `sportorg/gui/dialogs/event_properties.py` — dialog UI, set/apply values
- `sportorg/gui/main_window.py` — `set_title()` logic
- `sportorg/gui/dialogs/settings.py` — race selector label
- `sportorg/gui/dialogs/sportorg_import_dialog.py` — race selector label
- `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po` + `.mo`
- `sportorg/data/languages/en_US/LC_MESSAGES/sportorg.po` + `.mo`
