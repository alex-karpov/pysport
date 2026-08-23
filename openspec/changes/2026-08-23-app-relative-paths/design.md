# Design — application-relative data paths

## Context

Written against `master` (`b0391dd1`). The branch `ank/dev` is not merged into `master` and touches three of the files changed here; see "Known divergence" at the end.

## Decisions

| Question | Decision | Rationale |
|---|---|---|
| How are paths stored in `settings.json`? | Sentinel: empty means "resolve from `{app}`" | Matches the existing `sound_*_path` idiom (`Optional[str] = None` + `or config.sound_dir(...)`); keeps genuine user overrides intact |
| When is the package copied into `data/`? | First run only: no `settings.json` **and** no directory | Chosen deliberately over merge-on-every-start; the package tier of the resolution chain absorbs the resulting gap |
| Where does the installer put the program? | `Program Files` + `everyone-full` ACL on `data/` and `logs/` | Keeps `{app}` ASCII-only. A per-user install under `%LOCALAPPDATA%` would put Cyrillic in `{app}` for every user whose Windows account name is Cyrillic, which is common in the target audience and interacts with a known-but-unidentified Cyrillic path defect |
| Release artifacts | MSI + Inno `.exe` + portable `.zip` | — |
| Code structure | Dedicated `paths.py` + explicit `init()` | The feature requires a deterministic startup order; import-time side effects cannot express one |

## Roots

```python
# sportorg/paths.py — pure computation, no side effects on import
def app_dir(*p) -> str      # {app}: dirname(sys.executable) when frozen, else repository root
def package_dir(*p) -> str  # sportorg/data/... via importlib.resources
def data_dir(*p) -> str     # {app}/data/...
def log_dir(*p) -> str      # {app}/logs/...
```

`app_dir()` is the existing `config.module_path()` unchanged. It already yields `dirname(sys.executable)` for frozen builds and the repository root when running from source, so all three launch modes are covered by one definition — no source-specific branch is needed.

## Layout

| Directory | Root | Role |
|---|---|---|
| `img/`, `img/icon/` | package | immutable resources |
| `languages/<locale>/LC_MESSAGES/` | package | immutable resources |
| `styles/` | package | immutable resources (`STYLE_DIR` is currently unreferenced; retained deliberately) |
| `{app}/data/` | `{app}` | `settings.json`, `config.ini` (legacy), `rent_cards.txt` |
| `{app}/logs/` | `{app}` | `sportorg.log`, `sportorg-errors.log`, `si<date>.log` |
| `{app}/data/configs/` | `{app}` | reference tables, seeded from package |
| `{app}/data/templates/` | `{app}` | report templates, seeded from package |
| `{app}/data/sounds/` | `{app}` | sounds, seeded from package |

The last three exist in both places: the package copy is the reference, the `data/` copy is what the user may edit.

## Resolution order

For seeded directories:

1. explicit user override in `settings.json` — if non-empty
2. `{app}/data/<name>/` — if it exists
3. `package_dir(<name>)` — always exists

Tier 3 is load-bearing, not decorative. The chosen first-run trigger requires *both* the absence of `settings.json` and the absence of the directory, so upgrading an installation that already has `settings.json` performs no seeding while `{app}/data/templates/` does not yet exist. Without tier 3, `get_templates()` would call `os.listdir()` on a missing path and take down the report dialog. With it, the application reads the package copy: usable, though not editable.

## Startup sequence

```python
# SportOrg.pyw
def main() -> None:
    from sportorg.startup import init
    init()
    from sportorg.gui.main import Application
    Application().run()
```

`Application.__init__` constructs `QApplication` and `MainWindow`, so importing `sportorg.gui.main` pulls in the whole GUI and every module-level `translate()` call. `init()` must therefore run before that import; wrapping it in `main()` avoids an `E402` waiver.

`init()` performs four steps in order:

1. `paths.ensure_dirs()` — create `{app}/data/` and `{app}/logs/`.
2. `configure_logging()` — file handlers are created only now that `logs/` exists.
3. `paths.seed_if_first_run()` — for each of `configs`, `templates`, `sounds`, copy from the package when neither `settings.json` nor the target directory exists. Each copy is logged.
4. return to `main()` → GUI import → `Application().run()` → `load_settings()`.

Step 3 must precede settings load: `load_settings()` writes `settings.json` when migrating from `config.ini`, which would erase the first-run signal before it is read.

`LOG_CONFIG` is currently a module-level dict with `log_dir(...)` interpolated at import. It becomes `_build_log_config()`, called from `configure_logging()` after the directories exist.

`language.py` needs no change. It reads `config.SETTINGS_JSON` at import, and because `paths.py` is pure computation the constant already points at the new location whether or not `init()` has run.

## Error handling

- **`{app}` not writable** — portable unpacked into `Program Files`, or a read-only share. `ensure_dirs()` catches `OSError` and raises `PathsError`; `main()` catches it and shows a `QMessageBox` naming the path. Fatal, but comprehensible: today the same condition produces a `PermissionError` at import with no window and no visible output.
- **Seeding fails part-way** — `logging.exception`, continue. The resolution chain falls through to the package and the application stays usable.
- **Package directory missing** (broken build) — `logging.error`, continue. For `templates/` this means an empty report list with the reason recorded in the log.

Migration of data left in an old working directory is explicitly out of scope.

## Settings

Ten fields change their default to `""`: `templates_path` and the nine `source_*_path` fields. `sound_*_path` already use `None` as a sentinel and are left alone.

Resolution lives beside the existing `settings.template_dir()`:

```python
def configs_dir(*p) -> str:
    return paths.resolve_seeded("configs", *p)

def ranking_score_path() -> str:
    return SETTINGS.source_ranking_score_path or configs_dir("ranking.txt")
```

Nine such accessors. Inlining `or` at each call site would follow the `sound_*_path` precedent, but that precedent already duplicates `"ok.wav"` across `main.py` and `dialogs/settings.py`; named accessors keep each default in one place and give the settings dialog something to display.

### One-time migration

A new field `settings_version: int = 1` marks a pre-migration file. The dataclass default must be `1`, not the current version: `load_settings` fills missing keys from dataclass defaults, so defaulting to `2` would make every legacy file claim to be already migrated and the migration would never run. `CURRENT_SETTINGS_VERSION = 2` is written explicitly after a successful migration.

| Situation | Value read | Action |
|---|---|---|
| Legacy `settings.json`, key absent | `1` (default) | migrate → `2` → save |
| Already migrated | `2` from file | skip |
| First run, no file | `1` (default) | migration is a no-op, `2` written on first save |

A field is cleared only when **both** conditions hold:

1. the path does not exist on disk, **and**
2. its shape matches a former default — `source_*_path` ending in `configs/<expected-name>.txt`, `source_rent_cards_path` ending in `data/rent_cards.txt`, `templates_path` ending in `sportorg/data/templates` or `templates`.

Either condition alone is wrong. "Missing" alone would discard a deliberately chosen network path that happens to be offline. "Shape matches" alone would discard a live `D:\shared\configs\ranking.txt` the user picked by hand. Together they identify exactly the dead paths left behind by earlier installations.

Running once rather than on every start matters for the same reason: the heuristic reads the disk, and the disk is not always telling the truth at that moment.

`save_settings` merges into the existing JSON and preserves unknown keys (`libs/settings/__init__.py:9-13`), so clearing a field to `""` is written through and `settings_version` survives round-trips through older builds.

## Packaging

`git mv configs sportorg/data/configs` (nine files). `.gitignore` already negates `!sportorg/data/**`, so no ignore changes are needed. `builder.py` drops its separate `(config.base_dir("configs"), "configs")` entry — `sportorg/data` is already copied wholesale into `lib/sportorg/data`.

**MSI** — `bdist_msi_options["data"]` gains `Directory`, `CreateFolder` and `LockPermissions` rows, using the same mechanism that already declares `Shortcut`. This is the riskiest item in the change: MSI `LockPermissions` *replaces* the inherited ACL rather than extending it, and the modern `MsiLockPermissionsEx` table is not supported by cx_Freeze out of the box. Verification is mandatory — install the built MSI as a standard user and confirm the application starts and writes a log. If the tables prove unmanageable, stop and escalate rather than improvising a workaround.

**Inno** — `sportorg.iss` already carries a `[Dirs]` block with `Permissions: everyone-full`, but it lists `{app}\configs`, which becomes wrong once `configs` moves under `data`; that entry is dropped, leaving `data` and `logs`. Seeded subdirectories need no entries; the application creates them on first run and they inherit the parent ACL. Remaining fixes: `BuildDir` → `build\exe.win-amd64-3.8`; version passed from CI via `ISCC /D` instead of the hard-coded `v1.8.0`; `{pf}` → `{autopf}`; drop the `AdditionalLib32` block, a 32-bit Windows 7 workaround irrelevant to an x64 build.

**Portable** — no build-side work beyond packaging. On unpacking, `{app}` becomes the unpack directory, `settings.json` is absent, and first-run seeding creates and fills the directories. Pre-creating them inside the archive would be redundant and zip stores empty directories poorly.

**CI** — `release.yml` gains an ISCC step and a zip step after `builder.py build`; all three artifacts are attached to the release. Confirm `ISCC` is present on the `windows-latest` image, otherwise install it via `choco install innosetup`.

## Testing

`paths.py` has no import-time side effects, so tests substitute the root through one fixture pointing at `tmp_path` instead of monkey-patching module constants.

- `app_dir()` in both modes, via patched `sys.frozen` / `sys.executable`
- the `resolve_seeded` chain: user override → `data/` → package
- `seed_if_first_run` across all four combinations of `settings.json` and directory presence, plus a check that existing files are never overwritten
- migration: a dead old-shaped path is cleared; a live one is kept; a user path of a different shape is kept even when missing; a second run is a no-op
- `ensure_dirs()` raising `PathsError`, via a patched `os.makedirs` rather than real filesystem permissions

No existing test references the configuration directories. As a side effect, `pytest` stops creating `data/`, `configs/` and `logs/` in the working directory on every run.

## Known divergence from `ank/dev`

`ank/dev` (16 commits, not merged into `master`) touches three files changed here:

- `sportorg/logging.py` — does not exist on `master`; adds `DailyFileHandler` and `make_log_filename`
- `sportorg/config.py` — a different `LOG_CONFIG` handler block (dated rotating files instead of static names)
- `sportorg/settings.py` — `rogaine_photo_controls_path` and `NOVOSIVIRSK_ROGAINE_PAIRS` adjacent to the `source_*_path` block

All other files in this change are byte-identical between `master` and `ank/dev`. Merge conflicts in `config.py` and `settings.py` are expected when `ank/dev` is eventually merged; both are small and localised. The `LOG_CONFIG` → `_build_log_config()` conversion is the same edit on either side.
