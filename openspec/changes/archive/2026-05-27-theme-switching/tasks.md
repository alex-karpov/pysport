## 1. Settings field

- [x] 1.1 Add `theme: str = "system"` to the `Settings` dataclass in `sportorg/settings.py`
- [x] 1.2 Add round-trip tests in `tests/test_theme_settings.py` (default, save/reload, missing-key fallback)

## 2. Theme module

- [x] 2.1 Create `sportorg/gui/theme.py` with constants `THEME_SYSTEM` / `THEME_LIGHT` / `THEME_DARK` / `VALID_THEMES`, a module logger, and `_build_light_palette()` returning a default `QPalette`
- [x] 2.2 Replace `_build_light_palette()` to set every colour role explicitly (`Window` 239,239,239; `Base` 255,255,255; `Highlight` 48,140,198; etc.) — `QPalette()` and `QStyle.standardPalette()` both inherit OS-dark on Qt 6.5+ Windows 11
- [x] 2.3 Add `_build_dark_palette()` returning the canonical Fusion dark `QPalette` (`Window` 53,53,53; `Base` 42,42,42; `Highlight` 42,130,218; etc.)
- [x] 2.4 Add `detect_system_theme()` with fallback chain: Qt 6.5+ `colorScheme()` → `winreg` (Windows) → `defaults` (macOS) → `gsettings` (Linux) → `THEME_LIGHT`; swallow all exceptions at DEBUG level
- [x] 2.5 Add `apply_theme(app, choice)` orchestrator: validates choice, resolves `system`, installs Fusion style, clears stylesheet, applies the hand-built palette
- [x] 2.6 Add `_force_color_scheme(resolved)` helper that calls `QStyleHints.setColorScheme()` on Qt 6.8+ (no-op on older Qt / PySide2)
- [x] 2.7 Add unit tests in `tests/test_theme.py` (13 tests) covering constants, both palettes, detector branches, orchestrator, and `None`-app guard

## 3. Startup wiring

- [x] 3.1 In `sportorg/gui/main.py`, import `from sportorg.gui import theme` and call `theme.apply_theme(self.app, settings.SETTINGS.theme)` in `Application.run`, after the `load_settings` try/except and before `set_status_comments()`
- [x] 3.2 Remove `MainWindow._set_style` and its caller in `show_window` (`sportorg/gui/main_window.py`); the legacy `default.qss` reader was a no-op since the file is empty

## 4. Settings dialog

- [x] 4.1 In `sportorg/gui/dialogs/settings.py`, add `QApplication` to the PySide6/PySide2 import blocks and `from sportorg.gui import theme`
- [x] 4.2 In `MainTab.__init__`, add a `Theme` row immediately after the `Languages` row, before `Auto save`. Use an `AdvComboBox` populated from `_theme_options = [(THEME_SYSTEM, translate("System")), (THEME_LIGHT, translate("Light")), (THEME_DARK, translate("Dark"))]`; pre-select the index whose canonical key matches `SETTINGS.theme`, defaulting to index 0
- [x] 4.3 In `MainTab.save`, persist `SETTINGS.theme = self._theme_options[self.item_theme.currentIndex()][0]`
- [x] 4.4 In `SettingsDialog.apply_changes_impl`, call `theme.apply_theme(QApplication.instance(), settings.SETTINGS.theme)` after all `tab.save()` calls and before `main_window.refresh()`

## 5. Hardcoded-colour cleanups

- [x] 5.1 In `sportorg/gui/dialogs/about.py`, remove the line `licence_text.setStyleSheet("QScrollBar:vertical {background: #bfbfbf}")` (hardcoded gray scrollbar would clash with dark theme)
- [x] 5.2 In `sportorg/gui/tabs/log.py`, remove the unused `self.common_color = QtGui.QColor(0, 0, 0, 255)` attribute
- [x] 5.3 In `sportorg/gui/main_window.py`, replace `setTabTextColor(tab_index, self.logging_tab.common_color)` with `setTabTextColor(tab_index, QtGui.QColor())` — invalid `QColor` resets to palette foreground
- [x] 5.4 In `sportorg/gui/tabs/results.py`, add explicit foreground colour and `&nbsp;`-substitution to the three highlight spans: `background: red; color: white` (wrong split code) and `background: yellow; color: black` (extra/missing split). `&nbsp;` preserves monospace alignment that Qt rich-text would otherwise collapse

## 6. Translations

- [x] 6.1 Add to `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po`, immediately after the `msgid "Languages"` block: `Theme → "Тема оформления"`, `System → "Системная"`, `Light → "Светлая"`, `Dark → "Тёмная"`
- [x] 6.2 Run `uv run poe generate-mo` to compile `.mo` files

## 7. Changelog

- [x] 7.1 Add an entry to `changelog.md` and `changelog_ru.md` under the `## next` section's `### Improvements` (en) / `### Добавление` (ru) bullet list
