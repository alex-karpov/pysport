## 0. Setup

- [x] 0.1 Create worktree `C:\Users\ank\Documents\Prog\SportOrg\worktree\pysport-app-paths` on branch `ank/app-relative-paths` based on `master` (`b0391dd1`), **not** on `ank/dev` or `openspec-base`
- [x] 0.2 `uv sync --frozen --extra win --extra gui` in the worktree; confirm `uv run poe test` is green before any change — the worktree venv defaulted to Python 3.14 and failed to build `cx-logging`; recreated on 3.13, baseline 242 passed / 12 skipped

## 1. `sportorg/paths.py`

- [x] 1.1 Create `sportorg/paths.py` with no import-time side effects
- [x] 1.2 `app_dir(*p)` — `os.path.dirname(sys.executable)` when `hasattr(sys, "frozen")`, else the parent of the `sportorg` package (move the body of `config.module_path()`)
- [x] 1.3 `package_dir(*p)` — `importlib.resources` over `sportorg.data`; move `_RESOURCE_STACK` / `_RESOURCE_PATH_CACHE` / `package_data_path` here verbatim from `config.py`
- [x] 1.4 `data_dir(*p)` → `{app}/data`, `log_dir(*p)` → `{app}/logs`
- [x] 1.5 `SEEDED = ("configs", "templates", "sounds")`
- [x] 1.6 `resolve_seeded(name, *p, override="")` — override → `{app}/data/<name>` if `isdir` → `package_dir(name)`
- [x] 1.7 `class PathsError(Exception)`
- [x] 1.8 `ensure_dirs()` — `makedirs(data_dir(), log_dir(), exist_ok=True)`; wrap `OSError` in `PathsError` carrying the offending path
- [x] 1.9 `seed_if_first_run()` — per name in `SEEDED`: skip if `exists(SETTINGS_JSON)` **or** `isdir(data_dir(name))`; else `copytree(package_dir(name), data_dir(name))`; `logging.info` each copy; catch and `logging.exception` per name without aborting
- [x] 1.10 **Added during implementation:** `should_seed()` — false outside a frozen build. The brief says a source launch takes everything but `data/` and `logs/` from the package; seeding a checkout would also shadow `sportorg/data/`, so edits there would stop having any effect

## 2. `sportorg/config.py`

- [x] 2.1 Re-express `BASE_DIR`, `base_dir`, `module_path`, `IMG_DIR`, `img_dir`, `ICON_DIR`, `icon_dir`, `LOG_DIR`, `log_dir`, `DATA_DIR`, `data_dir`, `SOUND_DIR`, `sound_dir`, `STYLE_DIR`, `style_dir`, `LOCALE_DIR`, `locale_dir`, `TEMPLATE_DIR`, `CONFIG_INI`, `SETTINGS_JSON` as thin wrappers over `paths` — call sites stay untouched
- [x] 2.2 Delete `CONFIGS_DIR` and `config.configs_dir` — their only consumers are the `source_*_path` defaults, which become `""` in task 4.1; the resolver lives in `settings.py` instead
- [x] 2.3 Delete the `DIRS` list and the `for _DIR in DIRS: os.makedirs(...)` loop
- [x] 2.4 Convert the module-level `LOG_CONFIG` dict into `build_log_config()` so `log_dir(...)` is interpolated at call time, and delete the module-level `logging.config.dictConfig(LOG_CONFIG)` call — named without the leading underscore of the original plan, since `startup.py` calls it
- [x] 2.5 Keep `TEMPLATES_PATH` (`SPORTORG_TEMPLATES_PATH`) honoured — as the override *below* an explicit settings value, which is the precedence it had before (it only ever supplied the default for `templates_path`)
- [x] 2.6 **Added during implementation:** delete `runtime_dir` (the only source of `os.getcwd()` in path resolution), and the `SOUND_DIR` / `TEMPLATE_DIR` / `DEFAULT_TEMPLATE_DIR` constants, which would have frozen a pre-seeding answer at import time. `sound_dir()` resolves through `resolve_seeded`; `settings.template_dir()` owns template resolution. `config.SOUND_DIR`'s only consumer, `common/audio.py`, now calls `config.sound_dir()`

## 3. `sportorg/startup.py` and entry point

- [x] 3.1 Create `sportorg/startup.py` with `configure_logging()` calling `logging.config.dictConfig(config.build_log_config())`
- [x] 3.2 `init()` — `paths.ensure_dirs()` → `configure_logging()` → `paths.seed_if_first_run()`, in that order (guarded by `should_seed()`); also creates `SPORTORG_TEMPLATES_PATH` when set, which the deleted `DIRS` loop used to do
- [x] 3.3 Rewrite `SportOrg.pyw` as a `main()` that calls `init()` before `from sportorg.gui.main import Application` (avoids `E402`)
- [x] 3.4 Catch `PathsError` in `main()`; show `QMessageBox.critical` naming the path and reason; exit non-zero. Falls back to `stderr` when Qt is unavailable

## 4. Settings sentinel

- [x] 4.1 Change `templates_path` and the nine `source_*_path` defaults to `""`
- [x] 4.2 Add `settings_version: int = 1` to the dataclass and `CURRENT_SETTINGS_VERSION = 2` at module level
- [x] 4.3 Add `configs_dir(*p)` in `settings.py` delegating to `paths.resolve_seeded("configs", *p)`
- [x] 4.4 Add nine named accessors (`names_path()`, `middle_names_path()`, `countries_path()`, `groups_path()`, `regions_path()`, `status_comments_path()`, `status_default_comments_path()`, `ranking_score_path()`, `ranking_ardf_score_path()`) plus `rent_cards_path()`, each `override or default`
- [x] 4.5 Update `template_dir()` to `SETTINGS.templates_path or paths.resolve_seeded("templates")`
- [x] 4.6 Point call sites at the accessors: `gui/main.py` (`set_status_comments`, `set_countries`, `set_groups`, `set_names`, `set_middle_names`, `set_regions`, `set_ranking`, `set_ranking_ardf`, `set_rent_cards`), `models/constant.py:95`, and `gui/dialogs/rent_cards_dialog.py`

## 5. Settings migration

- [x] 5.1 Implement `_migrate_paths(settings)` — clear a field only when `not os.path.exists(value)` **and** the value matches a former-default shape (`configs/<name>.txt`, `data/rent_cards.txt`, `sportorg/data/templates`, `templates`); compare with normalised separators, case-insensitively. Compares whole path *segments*, not string suffixes, so `\\server\share\my-templates` is not mistaken for `templates`
- [x] 5.2 Wire into `load_settings_from_file()`: run when `settings_version < CURRENT_SETTINGS_VERSION`, then set the version and `save_settings_to_file()`
- [x] 5.3 `logging.info` each cleared field with its old value
- [x] 5.4 **Added during implementation:** expose the predicate as `sanitize_path(field, value)` and reuse it in `gui/main.py` for the `config.ini` → `settings.json` import, so a legacy `templates` directory recorded there does not arrive already migrated and untouchable

## 6. Package layout

- [x] 6.1 `git mv configs sportorg/data/configs` (nine `.txt` files)
- [x] 6.2 Remove `(config.base_dir("configs"), "configs")` from `include_files` in `builder.py`
- [x] 6.3 Verify `git status` shows the nine files tracked under the new path (`.gitignore` already negates `!sportorg/data/**`)

## 7. Installers

- [x] 7.1 `builder.py` — add `Directory`, `CreateFolder` and `LockPermissions` rows to `bdist_msi_options["data"]` for `{app}\data` and `{app}\logs`, granting `Everyone` write
- [x] 7.2 **Verification gate — DONE.** Not blocked after all: Python 3.8.10 is installed locally, so a separate `.venv38` builds the frozen tree and the MSI. `bdist_msi` accepted the rows, and dumping the built package with `msilib` (still present on 3.8) shows `CreateFolder` and `LockPermissions` carrying `Everyone` / `268435456` for both directories. Installed into `Program Files`; `icacls` reports `Все = Полный доступ` on `data` and `logs`
- [x] 7.2a **Found by that install:** the MSI was marked per-user (`all_users: False`), and Windows redirects `ProgramFilesFolder` to `%LOCALAPPDATA%\Programs` for a per-user install, so it offered `C:\Users\<User>\AppData\Local\Programs\sportorg\` — the Cyrillic-path exposure this change exists to avoid, and it also made the permissions pointless. Now `all_users: True` with `initial_target_dir` pinned to `[ProgramFiles64Folder]\SportOrg`, matching Inno. **Note for the release:** MSI cannot upgrade across install contexts, so an existing per-user installation must be removed by hand
- [x] 7.3 `sportorg.iss` — `BuildDir` → `build\exe.win-amd64-3.8`; accept `MyAppVersion` / `MyVersionInfoVersion` via `ISCC /D` with the current literals as fallback defaults; `{pf}` → `{autopf}`; delete the `AdditionalLib32` `[Files]` entry and its `#define`. Also sets `OutputDir=dist` so all three artifacts land together
- [x] 7.4 Confirm the existing `[Dirs]` block still lists only `data`, `logs` (and drop the now-redundant `configs` entry, since it moved under `data`)

## 8. CI

- [x] 8.1 `release.yml` — after `builder.py build`, add an ISCC step passing the version from `sportorg.config.VERSION`; checks for `ISCC` on `windows-latest` and falls back to `choco install innosetup`
- [x] 8.2 Add a step zipping the frozen build directory to `SportOrg-<version>-portable.zip`; the directory is discovered with a `build\exe.*` glob rather than hard-coded
- [x] 8.3 Extend `upload-artifact` and the release `files:` list to all three artifacts
- [x] 8.4 **Verified against a real run** (`workflow_dispatch` on `ank/app-relative-paths`, run 32691039071, green in 4m12s). The `Windows-x64` artifact carries all three files. The MSI's tables survive the CI build unchanged: `CreateFolder` = DataDir/LogDir, `LockPermissions` = `Everyone` / `268435456` for both, `ALLUSERS=2` with no `MSIINSTALLPERUSER`, `A_SET_TARGET_DIR` = `[ProgramFiles64Folder]\SportOrg`. The portable archive is flat — `SportOrg.exe`, `version`, `LICENSE` and both changelogs at the root, no stray `configs/`, and `lib/sportorg/data/{configs,templates,sounds,img,languages,styles}` present so seeding has something to copy

## 9. Tests

- [x] 9.1 `tests/test_paths.py` — fixture pointing `app_dir()` at `tmp_path`
- [x] 9.2 `app_dir()` frozen vs source, via patched `sys.frozen` / `sys.executable`
- [x] 9.3 `resolve_seeded` chain: override → `data/` → package
- [x] 9.4 `seed_if_first_run` across all four presence combinations; assert existing files are never overwritten
- [x] 9.5 `ensure_dirs()` raises `PathsError`, via patched `os.makedirs`
- [x] 9.6 `tests/test_settings_migration.py` — dead old-shaped path cleared; live path kept; foreign-shaped missing path kept; second run is a no-op; version written
- [x] 9.7 Confirm a `pytest` run no longer creates `data/`, `configs/` or `logs/` in the working directory — verified by deleting them and re-running

## 10. Manual verification

- [x] 10.1 Source launch from the repository root — `data/`, `logs/` appear at the root and **nothing is seeded** (amended from the original plan, see 1.10); templates, configs and sounds resolve to `sportorg/data/`
- [x] 10.2 Source launch with `cd` elsewhere — same locations, nothing created in the working directory
- [x] 10.3 Portable: first simulated by faking `sys.frozen` / `sys.executable` into an empty temporary directory — `data/` and `logs/` are created next to the "executable", all three directories are seeded from the package, and a second start preserves an edited `ranking.txt`. **Confirmed in Windows Sandbox** against the real build: launching the executable from another working directory still reads `settings.json` from `{app}`
- [x] 10.4 Inno install, **verified in Windows Sandbox**. It offers `C:\Program Files (x86)\SportOrg` by default (see 13.3); installed into `C:\Program Files\SportOrg`, `icacls` reports `Все = Полный доступ` on `data` and `logs`, the first run comes up with the shipped defaults (auto-save 300 s), and a launch from another working directory reads `settings.json` from `{app}`
- [x] 10.5 Upgrade path: a pre-migration `settings.json` with dead `configs/*.txt` paths clears exactly those fields, keeps a `D:\...` path of a different shape, writes `settings_version: 2`, preserves unrelated keys, and still renders the four report templates from the package copy — the tier-3 fallback doing what it was designed for

## 11. Release chores

- [x] 11.1 Bump `config.VERSION` to `v1.8.0b2` (and `pyproject.toml` / the project entry in `uv.lock`, which `uv sync --frozen` validates)
- [x] 11.2 Add entries to `changelog.md` and `changelog_ru.md` under `## next`
- [x] 11.3 `uv run poe all` green (format, lint, test at the 42% branch threshold) — 265 passed, 12 skipped, 50.24%
- [x] 11.4 **Added during implementation:** correct the project layout section of `AGENTS.md`, which pointed at the pre-`sportorg/data/` locations, and sync `CLAUDE.md` on the openspec branch

## 12. Found by installing the MSI

- [x] 12.1 MSI install context — see 7.2a
- [x] 12.2 Startup ran the `config.ini` import unconditionally, so a fresh installation adopted `Config()`'s pre-1.6 defaults instead of the dataclass ones: auto-save 5 s instead of 5 min (silently undoing #497 for every new user), UTF-8 saving and SRB generation on, sound disabled, and absolute sound paths frozen into `settings.json`. The import now runs only when `config.ini` exists
- [x] 12.3 The 5 the operator saw rather than the stored 0 comes from `gui/dialogs/settings.py`, where `AdvSpinBox(value=...)` is followed by `setMinimum(5)`; Qt raises the current value to the new minimum. Left alone — with 12.2 fixed the stored value is 300 and nothing is clamped. **Still open as a separate question:** 0 means "auto-save disabled" to `main_window.py`, but the dialog cannot express it and silently turns it into 5
- [x] 12.4 Moved the import out of `Application.load_settings` into `settings.load_settings_on_startup()` / `settings.import_legacy_config()`. Testing it in the GUI layer pulled PySide6 into the coverage run and dropped total coverage from 50% to 32%; the logic is settings logic and belongs there. Two dead fallbacks (`"logging_level", True` and `"log_window_row_count", True` for a `str` and an `int` field) corrected in passing
- [x] 12.5 Sound defaults resolve through `settings.successful_sound_path()` and friends instead of being written into `settings.json`. Without this, 12.2 would have made `sound_*_path` stay `None`, and `Sound._play` treats `None` as silence
- [x] 12.6 `tests/test_first_run_settings.py` — first run without `config.ini` keeps the dataclass defaults, writes `settings.json`, leaves the sound paths unset; a real `config.ini` is still imported; an existing `settings.json` still wins
- [x] 12.7 `load_settings_from_file` / `save_settings_to_file` take `Optional[str] = None` and resolve `config.SETTINGS_JSON` at call time — as default arguments they were frozen at import and no test could redirect them

**Behaviour change to be aware of:** `sound_enabled` now keeps its dataclass default of `True` on a fresh installation. The legacy import used to force it to `False`, so sounds were off out of the box.

## 13. Found in the Windows Sandbox pass

- [x] 13.1 MSI and Inno both install into `C:\Program Files\SportOrg` with `Все = Полный доступ` on `data` and `logs`, first run applies the shipped defaults, and a launch from another working directory reads `{app}`. Both the requirement and 12.2 hold on a clean machine
- [ ] 13.2 **Cosmetic, not fixed:** the two installers grant the same effective rights by different means, so the DACLs differ. MSI's `LockPermissions` *replaces* the descriptor and blocks inheritance, leaving `data` with exactly `Все:(OI)(CI)(F)` + `СИСТЕМА:(OI)(CI)(F)`; Inno's `Permissions: everyone-full` *adds* an ACE and keeps the inherited ones, so `data` also carries TrustedInstaller / Administrators / Users. Functionally equivalent — `Все` already covers every account that the inherited ACEs would have covered
- [x] 13.3 **Fixed.** Inno defaults to `C:\Program Files (x86)\SportOrg` because `sportorg.iss` declares no `ArchitecturesInstallIn64BitMode`, so `{autopf}` resolved to the 32-bit tree even though the payload is 64-bit. It predates this change — `master` had the same defect through `{pf}` — but it now contradicts 7.2a, which pinned the MSI to `[ProgramFiles64Folder]` so the two installers would agree. Added `ArchitecturesAllowed` / `ArchitecturesInstallIn64BitMode` = `x64compatible`; the script no longer references `{sys}`, so nothing else moves with the install mode. Recompiles clean under Inno Setup 6.7.3 (the spelling needs 6.3+; the release workflow installs current Inno via choco). Re-tested in Sandbox: the rebuilt installer offers `C:\Program Files\SportOrg`
- [ ] 13.4 **Not caused by this change:** the MSI sits ~2 min in *Preparing to install*, then ~2 min in *Installing*, before the progress bar moves. The frozen tree is 4049 files / 156 MB, and msiexec costs and extracts all of them from one MSZIP cabinet before reporting progress; Inno feels faster because it streams from a solid LZMA2 archive. Nothing in this change touches file count or packaging
- [x] 13.5 **Fixed** (pre-existing, surfaced while checking the CI artifacts). The MSI has no `Upgrade` table and `bdist_msi_options` sets no `upgrade_code`, so every build gets a fresh `ProductCode` and Windows treats each one as an unrelated product: installing 1.8.0 over 1.8.0b2 adds a second entry in *Программы и компоненты* pointing at the same directory, and uninstalling either one takes the shared files with it. `ProductVersion` compounds it — msilib requires a numeric version, so `1.8.0b2` is stored as `1.8.0` (the real value is kept in `DistVersion`). `bdist_msi_options` now sets `upgrade_code` to `{D652DEE1-13E6-4D7A-B8FC-334FF475E5FD}` — a random UUID4, fixed for good; a distinct GUID from the Inno `AppId`, which identifies the same product in a registry the two installers never share. `ProductCode` stays random per build, which is what a major upgrade requires. Verified in the rebuilt package: `FindRelatedProducts` at 200, `RemoveExistingProducts` at 1450, both `Upgrade` rows written, `LockPermissions` untouched.
  **Two limits remain, both inherent.** A copy installed from an MSI built *before* this commit carries no `UpgradeCode`, so `FindRelatedProducts` cannot see it — the 1.8.0b2 artifacts already handed out must be uninstalled by hand once. And because `ProductVersion` is truncated to `1.8.0`, the final 1.8.0 will not supersede 1.8.0b2 either: the removal row matches `< 1.8.0` only, and cx_Freeze writes no `LaunchCondition` on `REMOVENEWVERSION`, so the same-version case installs side by side without warning
