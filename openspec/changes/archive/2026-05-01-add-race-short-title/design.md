## Context

`RaceData` currently stores `title` (full event name) and `description` (subtitle). The window title uses `get_start_datetime()` as a short identifier when a file is open. Operators running multi-day events need a stable, concise label that is meaningless to participants but useful for the operator to orient themselves quickly.

The change touches the data model, JSON persistence, one dialog, the main window, two race-selector lists, and two translation catalogs.

## Goals / Non-Goals

**Goals:**
- Add `short_title: str` to `RaceData` with empty-string default
- Persist it in JSON; load old files gracefully via `.get("short_title", "")`
- Expose it in the Event Properties dialog with a date-based placeholder
- Replace the window title format to use `short_title` (or filename as fallback) as the leading label
- Show `short_title` (when set) in the multi-day race selector lists in Settings and Import dialogs
- Provide `ru_RU` and `en_US` translations for the new UI strings

**Non-Goals:**
- Showing `short_title` in printed protocols or split printouts
- Auto-populating `short_title` from `title` or any other field
- Syncing `short_title` to external live systems

## Decisions

**D1 — Backward compatibility via `.get()`, not migration hook.**
`RaceData.update_data` uses `str(data.get("short_title", ""))` instead of adding a branch to `_race_migrate`. Rationale: `_race_migrate` handles structural changes (renamed keys, nested objects); a missing optional string field is handled more cleanly at the model level. This keeps `_race_migrate` focused on non-trivial transformations.

**D2 — Window title fallback is `os.path.basename(self.file)` (with extension).**
When `short_title` is empty and a file is open, the window title uses the filename (e.g. `race_day1.json`) as the leading identifier instead of the datetime. This gives operators a stable label without requiring them to fill in `short_title`. The full path and datetime are still shown in brackets.

New format: `<label> [<datetime>] [<full_path>] — SportOrg <version>`
Where `<label>` = `short_title` if non-empty, else `os.path.basename(self.file)`.

**D3 — Placeholder is static (set once at dialog open).**
`item_short_title.setPlaceholderText(start_date.strftime("%Y.%m.%d"))` is called in `set_values_from_model`. No live update when the user edits the start date in the same dialog session. Rationale: the placeholder is a hint, not a live preview; adding a `dateTimeChanged` signal connection adds complexity for negligible UX gain.

**D4 — Em dash separator in window title.**
The current ` - ` separator is replaced with ` — ` (U+2014 em dash) for the new format. The `set_title(title=...)` branch is updated consistently.

**D5 — Race selector lists show `short_title` when non-empty.**
`settings.py` and `sportorg_import_dialog.py` currently display `str(cur_race.data.get_start_datetime())`. Both are updated to `short_title if short_title else str(get_start_datetime())`. This is a read-only display change with no behavioral side effects.

## Risks / Trade-offs

- **Window title change is visible to all users** — operators who relied on the datetime-first format will see a different layout. Mitigation: the datetime is still present in brackets; the change is additive.
- **Filename with extension as fallback** — on Windows, `.json` extension is always present. This is acceptable and expected by the user.
- **`.mo` files must be regenerated** — forgetting `uv run poe generate-mo` after editing `.po` files leaves translations stale. The `run` / `test` / `format` poe tasks all call `generate-mo` automatically, so this is only a risk for manual edits.

## Migration Plan

No database or file migration needed. Old JSON files load cleanly; `short_title` defaults to `""`. No rollback strategy needed — the field is additive and non-breaking.
