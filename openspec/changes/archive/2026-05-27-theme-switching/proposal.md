## Why

The application always uses the native Qt theme and provides no way to switch it. Operators working in a dark OS environment cannot get a dark UI; conversely, on a dark-OS Windows 11 with PySide6 ≥ 6.5 the application is forced into a dark palette by Qt with no way to opt back into light. A user-controlled `Light` / `Dark` / `System` choice, persisted across launches and applied without restart, fixes both directions.

## What Changes

- New `theme` field on `Settings` (`"system"` / `"light"` / `"dark"`, default `"system"`).
- New module `sportorg/gui/theme.py` encapsulating all theme logic: explicit hand-built light and dark `QPalette`, system theme detection, and a single `apply_theme(app, choice)` orchestrator.
- Theme applied at startup in `Application.run` (before any widget is shown) and live on OK from the Settings dialog (no restart needed).
- New row in `File → Settings → Main settings` between `Languages` and `Auto save`: combobox with `System` / `Light` / `Dark`.
- Removal of legacy `MainWindow._set_style()` (loaded an empty `default.qss`).
- Removal of hardcoded `#bfbfbf` scrollbar QSS in the About dialog.
- A few previously hardcoded widget colours made theme-aware: the Logs tab text colour (uses palette foreground instead of hardcoded black) and HTML `<span>` highlights in the result splits view (explicit `color:` paired with `background:` plus `&nbsp;` to preserve monospace alignment).
- New translations for `Theme` / `System` / `Light` / `Dark` in `ru_RU`.

## Capabilities

### New Capabilities
- `theme-switching`: user-selectable application theme (system/light/dark); persisted in settings; applied at startup and live on OK without restart.

### Modified Capabilities
_(no changes to existing specs)_

## Impact

**Changed files (code):**
- `sportorg/settings.py` — new `theme: str = "system"` field on `Settings` dataclass
- `sportorg/gui/theme.py` — new module (~210 lines)
- `sportorg/gui/main.py` — calls `apply_theme(self.app, settings.SETTINGS.theme)` in `Application.run` after `load_settings`
- `sportorg/gui/main_window.py` — removed `_set_style` method and its caller; Logs tab title colour now uses palette foreground
- `sportorg/gui/dialogs/settings.py` — Theme combobox added to `MainTab`; live `apply_theme` call in `apply_changes_impl`
- `sportorg/gui/dialogs/about.py` — removed hardcoded scrollbar stylesheet
- `sportorg/gui/tabs/log.py` — removed unused `common_color` attribute
- `sportorg/gui/tabs/results.py` — HTML span highlights gain explicit foreground colour and `&nbsp;` whitespace preservation
- `tests/test_theme.py` — new (13 unit tests)
- `tests/test_theme_settings.py` — new (3 round-trip tests)

**Changed files (i18n):**
- `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po` + `.mo`

**Dependencies:**
- No new runtime dependencies. Pure stdlib (`subprocess`, `winreg`, `sys`, `logging`) for OS detection.
- Compatible with PySide6 ≥ 6.0 and PySide2 ≥ 5.12 via the existing `try/except ModuleNotFoundError` import shim used across the GUI codebase.
- Python 3.8–3.14.

**Out of scope:**
- Live tracking of the OS theme during runtime (`System` is resolved once at startup; changing OS theme mid-session has no effect).
- Dark variants of HTML report templates (`sportorg/data/templates/*.html`) — printed and exported documents stay light regardless of GUI theme.
- Dark variants of bundled PNG/SVG icons.
- Physical deletion of legacy `sportorg/data/styles/light.qss` and `default.qss` (no longer read by code; left on disk for a separate cleanup change).
