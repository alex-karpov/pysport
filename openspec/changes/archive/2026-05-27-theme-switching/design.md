## Context

The application currently runs in whatever palette Qt picks for the OS at startup. On PySide6 ≥ 6.5 / Windows 11 with a dark OS theme, Qt's QPA platform theme silently injects a dark palette into the `QApplication`, with no user control. PySide2 ignores OS dark mode entirely, so the same operator gets opposite behaviour on the two bindings. `MainWindow._set_style()` loaded an empty `default.qss` from disk — effectively a no-op, but a misleading hook.

This change adds an explicit, deterministic theme layer between Qt and the user.

## Goals / Non-Goals

**Goals:**
- Three-value theme selector: `system` / `light` / `dark`, persisted in `settings.json`.
- Same behaviour across PySide2 / PySide6 6.0–6.x / Python 3.8–3.14.
- Theme applied before the first widget is painted (no flash of OS-default on startup).
- Live switching on OK in Settings without restarting the application.
- "Light" actually renders light even on Windows 11 dark OS.

**Non-Goals:**
- Tracking OS theme changes during runtime. `System` is resolved once at startup.
- Restyling printed HTML templates (`sportorg/data/templates/`).
- Bundled icons remain as-is (multi-colour SVGs / PNGs, visible enough on either theme).
- Deleting the legacy `light.qss` / `default.qss` files on disk.

## Decisions

### D1 — Fusion style + explicit `QPalette` instead of `setColorScheme()` alone

Qt's `QStyleHints.setColorScheme()` was added in Qt 6.8 (the Qt 6.5 addition was a read-only getter). Using it as the only mechanism would silently fail on PySide6 6.5–6.7 and on PySide2 entirely.

Chosen mechanism: `QApplication.setStyle(QStyleFactory.create("Fusion"))` + `QApplication.setPalette(<explicit palette>)`. Fusion draws every widget using palette colour roles, so a single `setPalette` call recolours the entire UI deterministically. On Qt 6.8+ we additionally call `setColorScheme()` so Qt's platform theme stops re-applying the OS palette on top of ours — but the explicit palette is the load-bearing mechanism, not `setColorScheme`.

Trade-off: writing both palettes by hand (≈20 colour roles each, 2 themes) is more code than delegating to Qt. The win is determinism across bindings and Qt versions.

### D2 — Palettes are hand-built, not derived from `QPalette()` / `QStyle.standardPalette()`

On PySide6 ≥ 6.5 + Windows 11 dark OS, both `QPalette()` (no-arg constructor) and `QStyle.standardPalette()` inherit the OS-supplied dark palette. So `_build_light_palette()` cannot just return `QPalette()` — it would render dark. Both `_build_light_palette` and `_build_dark_palette` therefore set every role explicitly via `setColor`, mirroring each other in structure.

The canonical Fusion light values were picked (`Window` 239,239,239; `Base` 255,255,255; `Highlight` 48,140,198; etc.); dark values follow the widely used "Qt Fusion dark" recipe (`Window` 53,53,53; `Base` 42,42,42; `Highlight` 42,130,218).

### D3 — System detection: Qt API first, OS-specific fallback chain, light default

`detect_system_theme()` tries, in order:
1. `QGuiApplication.styleHints().colorScheme()` (Qt 6.5+).
2. Windows: `winreg` read of `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`.
3. macOS: `defaults read -g AppleInterfaceStyle` (non-zero exit ⇒ Light, per Apple's own contract).
4. Linux: `gsettings get org.gnome.desktop.interface color-scheme`.
5. Any failure ⇒ `THEME_LIGHT` (safe default).

All exceptions in detection are swallowed at `_LOGGER.debug` level. Theme detection must never block application startup.

### D4 — Static resolution at startup, no live OS tracking

When the user picks `System`, `detect_system_theme()` is called once at startup and again only when the user clicks OK in Settings. Qt's `colorSchemeChanged` signal is not wired up. Rationale: simplicity and predictability — competition operators rarely change OS theme mid-event, and live tracking would add platform-specific glue. Explicit choice (Light/Dark) of course is also static.

### D5 — Theme applied in `Application.run`, after `load_settings`, before `show_window`

```
Application.run()
  load_settings()           ← settings.SETTINGS.theme available
  apply_theme(app, theme)   ← palette set before any widget is created
  set_status_comments() ... ← other startup data loading
  main_window.show_window()
```

This guarantees no flash of light theme before dark applies (or vice versa). `MainWindow.__init__` creates no widgets; widgets are constructed inside `show_window`.

### D6 — Live apply in `SettingsDialog.apply_changes_impl`

```python
for tab, _ in self.widgets:
    tab.save()                                              # writes SETTINGS.theme
theme.apply_theme(QApplication.instance(), SETTINGS.theme)  # NEW
main_window.refresh_menu()
main_window.refresh()
settings.save_settings_to_file()
```

`QApplication.setPalette()` emits `QEvent.PaletteChange` to all existing widgets, including the open Settings dialog itself. Under Fusion the repaint is automatic; no explicit traversal needed.

### D7 — Combobox stores canonical English keys

`_theme_options` is `[(key, translated_label), ...]`: the canonical string (`"system"`/`"light"`/`"dark"`) is stored in `SETTINGS.theme` and `settings.json`, the translated label (`"Системная"`/`"Светлая"`/`"Тёмная"`) is shown in the combobox. Two parallel arrays would create a synchronisation hazard; the tuple list is one source of truth.

### D8 — Hardcoded widget colours fixed alongside the theme switcher

Three pre-existing hardcoded colour sites broke dark theme readability and are fixed in the same change:
- `sportorg/gui/dialogs/about.py:82` — hardcoded `#bfbfbf` scrollbar QSS removed (lets the palette drive the scrollbar).
- `sportorg/gui/tabs/log.py:15` + `main_window.py:617` — Logs tab title colour: passing an invalid `QColor()` resets to palette foreground instead of a hardcoded black.
- `sportorg/gui/tabs/results.py` — HTML span highlights for split mismatches: explicit `color: black` / `color: white` paired with `background: yellow` / `background: red`, plus `s.replace(" ", "&nbsp;")` to preserve monospace alignment (Qt rich-text collapses consecutive whitespace inside `<span>`).

## Risks / Trade-offs

- **Hand-built palettes** — must be updated if Qt changes its rendering. Mitigated by unit tests asserting specific colour values for both palettes.
- **`setStyleSheet("")` in `apply_theme`** — defensively clears any legacy QSS that might have been set elsewhere. If a future feature legitimately wants a global QSS, it must compose with the theme layer rather than being set independently.
- **Plain `QColor()` reset trick in `main_window.py`** — relies on documented `setTabTextColor` behaviour ("invalid colour ⇒ use palette role"). Behavioural change in Qt would silently re-introduce the dark-on-dark bug; a UI smoke test on dark theme catches it.
- **System detection on Linux** — `gsettings` is GNOME-only. KDE / XFCE users with `system` selected will silently fall back to Light. Acceptable for the primary user base (Windows-only competition operators); can be extended later if Linux usage grows.

## Migration Plan

No data migration. The new `theme` field defaults to `"system"`, so existing `settings.json` files without it load cleanly. No rollback strategy needed — the change is additive at the data layer.

## Compatibility Matrix

| Python | PySide2 5.15 | PySide6 ≤ 6.4 | PySide6 6.5–6.7 | PySide6 ≥ 6.8 |
|--------|--------------|---------------|------------------|---------------|
| 3.8    | Fusion + palette + winreg/defaults/gsettings detect | same | + Qt `colorScheme()` read | + `setColorScheme()` write |
| 3.9–3.13 | n/a | same | same | same |
| 3.14   | n/a | same | same | same |

No code path is gated by Python version; every Qt-version-specific feature is probed via `hasattr` or `try`.
