## ADDED Requirements

### Requirement: theme field on Settings

`Settings` SHALL have a `theme: str` attribute with default value `"system"`. Valid values are `"system"`, `"light"`, `"dark"`. The field SHALL round-trip through `save_settings_to_file` / `load_settings_from_file`. Loading a `settings.json` that lacks the key SHALL default to `"system"` without raising.

#### Scenario: Default value
- **WHEN** a fresh `Settings()` instance is created
- **THEN** `theme` equals `"system"`

#### Scenario: Round trip
- **WHEN** `theme` is set to `"dark"`, saved to a file, then reloaded into a new `Settings` instance
- **THEN** the loaded `theme` equals `"dark"`

#### Scenario: Backward compatibility
- **WHEN** a `settings.json` is loaded that does not contain the `theme` key
- **THEN** `theme` is set to `"system"` and no exception is raised

### Requirement: System theme detection

The function `detect_system_theme()` in `sportorg/gui/theme.py` SHALL return either `"light"` or `"dark"`, never any other value. Detection SHALL try, in order: Qt's `QStyleHints.colorScheme()` (when available, Qt 6.5+); then the OS-specific source (`winreg` on Windows, `defaults` on macOS, `gsettings` on Linux). On any error or unsupported platform, the function SHALL return `"light"`. Errors SHALL be logged at DEBUG level and SHALL NOT propagate.

#### Scenario: Returns a known value
- **WHEN** `detect_system_theme()` is called on any supported platform
- **THEN** the return value is `"light"` or `"dark"`

#### Scenario: Qt source preferred when available
- **WHEN** Qt exposes `Qt.ColorScheme` and `styleHints().colorScheme()` returns `Dark`
- **THEN** `detect_system_theme()` returns `"dark"` without consulting OS-specific sources

#### Scenario: Detection failure does not raise
- **WHEN** both the Qt and OS detection paths raise an exception
- **THEN** `detect_system_theme()` returns `"light"` and the exception is logged at DEBUG level

### Requirement: apply_theme orchestrator

The function `apply_theme(app, choice)` SHALL accept an optional `QApplication` and a string choice. If `app` is `None`, the function SHALL return without side effects. If `choice` is not one of `{"system", "light", "dark"}`, the function SHALL treat it as `"system"`. For `"system"`, the function SHALL resolve the effective theme via `detect_system_theme()`. The function SHALL then: install the `Fusion` style on the application, clear any existing stylesheet, install the appropriate hand-built palette (`_build_dark_palette()` for dark, `_build_light_palette()` for light), and on Qt 6.8+ set the corresponding `QStyleHints.colorScheme()`.

#### Scenario: Light choice
- **WHEN** `apply_theme(app, "light")` is called
- **THEN** `app.setStyle(<Fusion>)`, `app.setStyleSheet("")`, and `app.setPalette(<light palette>)` are invoked

#### Scenario: Dark choice
- **WHEN** `apply_theme(app, "dark")` is called
- **THEN** the applied palette has `Window` colour `(53, 53, 53)` in the Active group

#### Scenario: System choice resolved via detector
- **WHEN** `detect_system_theme()` returns `"dark"` and `apply_theme(app, "system")` is called
- **THEN** the dark palette is applied

#### Scenario: Invalid choice falls back to system
- **WHEN** `apply_theme(app, "garbage")` is called
- **THEN** the function does not raise and applies the theme resolved by `detect_system_theme()`

#### Scenario: None app is a no-op
- **WHEN** `apply_theme(None, "light")` is called
- **THEN** the function returns without raising

### Requirement: Theme applied at startup before first widget

The theme SHALL be applied in `Application.run`, after `Application.load_settings()` succeeds (or its exception is logged) and before `main_window.show_window()` is called. The user SHALL NOT see a flash of the OS-default palette before the chosen theme takes effect.

#### Scenario: Startup with dark theme
- **WHEN** the application starts with `SETTINGS.theme = "dark"`
- **THEN** the main window appears in the dark palette from its first paint, with no transient light frame

### Requirement: Live application on OK in Settings

`SettingsDialog.apply_changes_impl` SHALL call `apply_theme(QApplication.instance(), SETTINGS.theme)` after all tabs have saved and before `main_window.refresh()`. The theme SHALL be visible in the running application immediately, without restart.

#### Scenario: Switching from light to dark on OK
- **WHEN** the user changes the Theme combobox from `Light` to `Dark` and clicks OK
- **THEN** the main window and any open dialogs repaint with the dark palette without restarting the application

### Requirement: Theme combobox in Settings Main tab

`MainTab` of the Settings dialog SHALL contain a row labelled `Theme` between the existing `Languages` row and the `Auto save` row. The row SHALL be a combobox with three options whose canonical values are `system`, `light`, `dark` and whose displayed labels are translated via `translate()`. The combobox SHALL pre-select the option matching `SETTINGS.theme`; an unrecognised stored value SHALL pre-select the first option. `MainTab.save()` SHALL write the canonical value (not the localised label) to `SETTINGS.theme`.

#### Scenario: Combobox reflects stored value
- **WHEN** the Settings dialog opens with `SETTINGS.theme = "dark"`
- **THEN** the Theme combobox shows the localised label for "Dark" selected

#### Scenario: Selection persists the canonical key
- **WHEN** the user selects "Dark" from the combobox and `save()` runs
- **THEN** `SETTINGS.theme` equals `"dark"` (the English canonical key, not the localised label)

### Requirement: Russian translations

The strings `"Theme"`, `"System"`, `"Light"`, `"Dark"` SHALL have entries in `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po`. The `.mo` file SHALL be regenerated after the `.po` is updated.

#### Scenario: ru_RU Theme label
- **WHEN** the locale is `ru_RU` and the Settings dialog opens
- **THEN** the Theme row label shows `"Тема оформления"` and the combobox options show `"Системная"`, `"Светлая"`, `"Тёмная"`
