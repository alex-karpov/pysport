## Why

SportOrg resolves its writable directories from the **current working directory**: `config.py` defines `runtime_dir()` as `os.getcwd()` and derives `data/`, `configs/` and `logs/` from it. The location of a user's settings, logs and reference tables therefore depends on where the process happened to be started, not on where the program is installed.

This produces three concrete failures:

- **Installed builds crash for non-privileged users.** `config.py` runs `os.makedirs(...)` at *import time*. Installed under `Program Files` without an ACL on the data directories, that raises `PermissionError` before Qt is initialised — under `base="Win32GUI"` there is no console and no window, so the application simply fails to appear.
- **The MSI installer creates nothing.** `bdist_msi_options` declares only a `Shortcut`; `data/` and `logs/` are never pre-created and never get write permissions. Only `sportorg.iss` has the required `[Dirs]` block, and that script is stale and not wired into CI.
- **Reference data is unreachable after a fresh install.** `configs/` lives in the repository root, outside the `sportorg.data` package. Started from any directory that has no `configs/`, the application logs an exception per missing file and silently runs with an empty ranking table.

A related defect blocks any fix: absolute paths for `templates_path` and the nine `source_*_path` settings are persisted into `settings.json` and override the defaults on load, so changing the defaults alone has no effect on existing installations.

## What Changes

- New module `sportorg/paths.py` — side-effect-free resolution of three roots: `app_dir()` (the program location, `{app}`), `package_dir()` (immutable resources shipped in `sportorg/data/`) and `data_dir()` / `log_dir()` (writable state under `{app}`).
- Writable state moves from the working directory to `{app}`: `{app}/data/`, `{app}/logs/`, and the seeded `{app}/data/configs/`, `{app}/data/templates/`, `{app}/data/sounds/`.
- `configs/` moves from the repository root into the package as `sportorg/data/configs/`, becoming the seed source alongside `templates/` and `sounds/`.
- Three-step resolution for seeded directories: explicit user override → `{app}/data/<name>/` → `package_dir(<name>)`. The package tier guarantees the application stays usable when a data directory is absent.
- First-run seeding: when `settings.json` does not exist **and** a seeded directory does not exist, its contents are copied from the package.
- Explicit startup sequence replacing import-time side effects: `ensure_dirs()` → `configure_logging()` → `seed_if_first_run()` → settings load. `SportOrg.pyw` calls `init()` before importing the GUI.
- Sentinel path settings: `templates_path` and the nine `source_*_path` fields default to `""`, meaning "resolve from `{app}`". A one-time migration guarded by a new `settings_version` field clears stale values left by previous versions.
- All three release artifacts build in CI: MSI (with `CreateFolder` + `LockPermissions`), an Inno Setup `.exe`, and a portable `.zip`.

## Capabilities

### New Capabilities
- `app-data-paths`: resolve program resources and writable state relative to the program location rather than the working directory, seed writable directories from the package on first run, and pre-create them with write permissions at install time

### Modified Capabilities
- none

## Impact

- **Behaviour change:** a shortcut whose "Start in" directory differs from the program directory previously produced a separate set of data; those files stay where they are and are not migrated. Installed builds are unaffected — the shortcut already sets `WkDir=TARGETDIR`.
- **Release artifacts:** the release gains an Inno `.exe` and a portable `.zip` alongside the existing `.msi`.
- **Repository layout:** the root `configs/` directory is removed; its files live in `sportorg/data/configs/`.
