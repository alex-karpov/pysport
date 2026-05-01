## 1. Data Model

- [x] 1.1 Add `self.short_title: str = ""` to `RaceData.__init__` in `sportorg/models/memory.py`
- [x] 1.2 Add `"short_title": self.short_title` to `RaceData.to_dict()`
- [x] 1.3 Add `self.short_title = str(data.get("short_title", ""))` to `RaceData.update_data()`

## 2. Event Properties Dialog

- [x] 2.1 In `set_values_from_model`: add `self.item_short_title.setText(str(obj.data.short_title))` and `self.item_short_title.setPlaceholderText(obj.data.get_start_datetime().strftime("%Y.%m.%d"))`
- [x] 2.2 In `apply_changes_impl`: add `obj.data.short_title = self.item_short_title.text()`

## 3. Window Title

- [x] 3.1 Rewrite `MainWindow.set_title()` in `sportorg/gui/main_window.py` to use format `"<label> [<datetime>] [<full_path>] — SportOrg <version>"` where `<label>` = `short_title` if non-empty, else `os.path.basename(self.file)`
- [x] 3.2 Update the `set_title(title=...)` branch to use ` — ` em dash separator (was ` - `)

## 4. Race Selector Lists

- [x] 4.1 In `sportorg/gui/dialogs/settings.py`: replace `str(cur_race.data.get_start_datetime())` with `cur_race.data.short_title or str(cur_race.data.get_start_datetime())`
- [x] 4.2 In `sportorg/gui/dialogs/sportorg_import_dialog.py`: same replacement as 4.1

## 5. Translations

- [x] 5.1 Add to `sportorg/data/languages/ru_RU/LC_MESSAGES/sportorg.po`: entry for `"Short title"` → `"Короткое название"` and tooltip entry → `"Только для оператора. Отображается в заголовке окна и списке соревнований, в протоколах не печатается."`
- [x] 5.2 Add to `sportorg/data/languages/en_US/LC_MESSAGES/sportorg.po`: entries for same keys with `msgstr = msgid`
- [x] 5.3 Run `uv run poe generate-mo` to recompile `.mo` files
