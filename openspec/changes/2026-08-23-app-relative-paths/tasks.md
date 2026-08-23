## 0. Setup

- [ ] 0.1 Create worktree `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-app-paths` on branch `ank/app-relative-paths` based on `master` (`b0391dd1`), **not** on `ank/dev` or `openspec-base`
- [ ] 0.2 `uv sync --frozen --extra win --extra gui` in the worktree; confirm `uv run poe test` is green before any change

## 1. `sportorg/paths.py`

- [ ] 1.1 Create `sportorg/paths.py` with no import-time side effects
- [ ] 1.2 `app_dir(*p)` — `os.path.dirname(sys.executable)` when `hasattr(sys, "frozen")`, else the parent of the `sportorg` package (move the body of `config.module_path()`)
- [ ] 1.3 `package_dir(*p)` — `importlib.resources` over `sportorg.data`; move `_RESOURCE_STACK` / `_RESOURCE_PATH_CACHE` / `package_data_path` here verbatim from `config.py`
- [ ] 1.4 `data_dir(*p)` → `{app}/data`, `log_dir(*p)` → `{app}/logs`
- [ ] 1.5 `SEEDED = ("configs", "templates", "sounds")`
- [ ] 1.6 `resolve_seeded(name, *p, override="")` — override → `{app}/data/<name>` if `isdir` → `package_dir(name)`
- [ ] 1.7 `class PathsError(Exception)`
- [ ] 1.8 `ensure_dirs()` — `makedirs(data_dir(), log_dir(), exist_ok=True)`; wrap `OSError` in `PathsError` carrying the offending path
- [ ] 1.9 `seed_if_first_run()` — per name in `SEEDED`: skip if `exists(SETTINGS_JSON)` **or** `isdir(data_dir(name))`; else `copytree(package_dir(name), data_dir(name))`; `logging.info` each copy; catch and `logging.exception` per name without aborting

## 2. `sportorg/config.py`

- [ ] 2.1 Re-express `BASE_DIR`, `base_dir`, `module_path`, `IMG_DIR`, `img_dir`, `ICON_DIR`, `icon_dir`, `LOG_DIR`, `log_dir`, `DATA_DIR`, `data_dir`, `SOUND_DIR`, `sound_dir`, `STYLE_DIR`, `style_dir`, `LOCALE_DIR`, `locale_dir`, `TEMPLATE_DIR`, `CONFIG_INI`, `SETTINGS_JSON` as thin wrappers over `paths` — call sites stay untouched
- [ ] 2.2 Delete `CONFIGS_DIR` and `config.configs_dir` — their only consumers are the `source_*_path` defaults, which become `""` in task 4.1; the resolver lives in `settings.py` instead
- [ ] 2.3 Delete the `DIRS` list and the `for _DIR in DIRS: os.makedirs(...)` loop
- [ ] 2.4 Convert the module-level `LOG_CONFIG` dict into `_build_log_config()` so `log_dir(...)` is interpolated at call time, and delete the module-level `logging.config.dictConfig(LOG_CONFIG)` call
- [ ] 2.5 Keep `TEMPLATES_PATH` (`SPORTORG_TEMPLATES_PATH`) honoured as the package-tier override

## 3. `sportorg/startup.py` and entry point

- [ ] 3.1 Create `sportorg/startup.py` with `configure_logging()` calling `logging.config.dictConfig(config._build_log_config())`
- [ ] 3.2 `init()` — `paths.ensure_dirs()` → `configure_logging()` → `paths.seed_if_first_run()`, in that order
- [ ] 3.3 Rewrite `SportOrg.pyw` as a `main()` that calls `init()` before `from sportorg.gui.main import Application` (avoids `E402`)
- [ ] 3.4 Catch `PathsError` in `main()`; show `QMessageBox.critical` naming the path and reason; exit non-zero

## 4. Settings sentinel

- [ ] 4.1 Change `templates_path` and the nine `source_*_path` defaults to `""`
- [ ] 4.2 Add `settings_version: int = 1` to the dataclass and `CURRENT_SETTINGS_VERSION = 2` at module level
- [ ] 4.3 Add `configs_dir(*p)` in `settings.py` delegating to `paths.resolve_seeded("configs", *p)`
- [ ] 4.4 Add nine named accessors (`names_path()`, `middle_names_path()`, `countries_path()`, `groups_path()`, `regions_path()`, `status_comments_path()`, `status_default_comments_path()`, `ranking_score_path()`, `ranking_ardf_score_path()`) plus `rent_cards_path()`, each `override or default`
- [ ] 4.5 Update `template_dir()` to `SETTINGS.templates_path or paths.resolve_seeded("templates")`
- [ ] 4.6 Point call sites at the accessors: `gui/main.py` (`set_status_comments`, `set_countries`, `set_groups`, `set_names`, `set_middle_names`, `set_regions`, `set_ranking`, `set_ranking_ardf`, `set_rent_cards`) and `models/constant.py:95`

## 5. Settings migration

- [ ] 5.1 Implement `_migrate_paths(settings)` — clear a field only when `not os.path.exists(value)` **and** the value matches a former-default shape (`configs/<name>.txt`, `data/rent_cards.txt`, `sportorg/data/templates`, `templates`); compare with normalised separators, case-insensitively
- [ ] 5.2 Wire into `load_settings_from_file()`: run when `settings_version < CURRENT_SETTINGS_VERSION`, then set the version and `save_settings_to_file()`
- [ ] 5.3 `logging.info` each cleared field with its old value

## 6. Package layout

- [ ] 6.1 `git mv configs sportorg/data/configs` (nine `.txt` files)
- [ ] 6.2 Remove `(config.base_dir("configs"), "configs")` from `include_files` in `builder.py`
- [ ] 6.3 Verify `git status` shows the nine files tracked under the new path (`.gitignore` already negates `!sportorg/data/**`)

## 7. Installers

- [ ] 7.1 `builder.py` — add `Directory`, `CreateFolder` and `LockPermissions` rows to `bdist_msi_options["data"]` for `{app}\data` and `{app}\logs`, granting `Everyone` write
- [ ] 7.2 **Verification gate:** build the MSI, install as a standard (non-admin) user, confirm the application starts and writes `logs\sportorg.log`. If `LockPermissions` proves unmanageable, stop and report rather than improvising
- [ ] 7.3 `sportorg.iss` — `BuildDir` → `build\exe.win-amd64-3.8`; accept `MyAppVersion` / `MyVersionInfoVersion` via `ISCC /D` with the current literals as fallback defaults; `{pf}` → `{autopf}`; delete the `AdditionalLib32` `[Files]` entry and its `#define`
- [ ] 7.4 Confirm the existing `[Dirs]` block still lists only `data`, `logs` (and drop the now-redundant `configs` entry, since it moved under `data`)

## 8. CI

- [ ] 8.1 `release.yml` — after `builder.py build`, add an ISCC step passing the version from `sportorg.config.VERSION`; check whether `ISCC` exists on `windows-latest`, otherwise `choco install innosetup`
- [ ] 8.2 Add a step zipping `build\exe.win-amd64-3.8\` to `SportOrg-<version>-portable.zip`
- [ ] 8.3 Extend `upload-artifact` and the release `files:` list to all three artifacts

## 9. Tests

- [ ] 9.1 `tests/test_paths.py` — fixture pointing `app_dir()` at `tmp_path`
- [ ] 9.2 `app_dir()` frozen vs source, via patched `sys.frozen` / `sys.executable`
- [ ] 9.3 `resolve_seeded` chain: override → `data/` → package
- [ ] 9.4 `seed_if_first_run` across all four presence combinations; assert existing files are never overwritten
- [ ] 9.5 `ensure_dirs()` raises `PathsError`, via patched `os.makedirs`
- [ ] 9.6 `tests/test_settings_migration.py` — dead old-shaped path cleared; live path kept; foreign-shaped missing path kept; second run is a no-op; version written
- [ ] 9.7 Confirm a `pytest` run no longer creates `data/`, `configs/` or `logs/` in the working directory

## 10. Manual verification

- [ ] 10.1 Source launch from the repository root — `data/`, `logs/` appear at the root; `data/configs`, `data/templates`, `data/sounds` seeded on a clean checkout
- [ ] 10.2 Source launch with `cd` elsewhere — same locations, nothing created in the working directory
- [ ] 10.3 Portable: unpack the zip into an empty directory, run, confirm all directories are created and seeded next to the executable
- [ ] 10.4 Inno install as standard user — start, generate a report, confirm `logs\sportorg.log` is written
- [ ] 10.5 Upgrade path: place a pre-migration `settings.json` with dead `configs/*.txt` paths, start, confirm the fields are cleared, `settings_version` is `2`, and reports still render from the package templates

## 11. Release chores

- [ ] 11.1 Bump `config.VERSION` to `v1.8.0b2`
- [ ] 11.2 Add entries to `changelog.md` and `changelog_ru.md` under `## next`
- [ ] 11.3 `uv run poe all` green (format, lint, test at the 42% branch threshold)
