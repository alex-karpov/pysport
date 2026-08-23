## ADDED Requirements

### Requirement: Paths resolved relative to the program, not the working directory
The system SHALL provide `sportorg/paths.py` exposing `app_dir()`, `package_dir()`, `data_dir()` and `log_dir()`. `app_dir()` SHALL return `os.path.dirname(sys.executable)` when `sys.frozen` is set, and the repository root (the parent of the `sportorg` package) otherwise. `data_dir()` SHALL resolve to `{app}/data` and `log_dir()` to `{app}/logs`. The module SHALL NOT create directories, configure logging, or perform any other side effect at import time. `os.getcwd()` SHALL NOT influence any resolved path.

#### Scenario: Frozen build resolves next to the executable
- **WHEN** `sys.frozen` is set and `sys.executable` is `C:\Program Files\SportOrg\SportOrg.exe`
- **THEN** `app_dir()` returns `C:\Program Files\SportOrg` and `data_dir()` returns `C:\Program Files\SportOrg\data`

#### Scenario: Source launch resolves to the repository root
- **WHEN** `sys.frozen` is not set
- **THEN** `app_dir()` returns the parent directory of the `sportorg` package

#### Scenario: Working directory is irrelevant
- **WHEN** the process is started from a directory other than `app_dir()`
- **THEN** `data_dir()` and `log_dir()` are unchanged

#### Scenario: Import has no side effects
- **WHEN** `sportorg.paths` is imported
- **THEN** no directory is created and logging is not configured

### Requirement: Three-tier resolution for seeded directories
The system SHALL resolve each of `configs`, `templates` and `sounds` through `paths.resolve_seeded(name, *parts)` in this order: a non-empty user override from settings, then `{app}/data/<name>/` when that directory exists, then `package_dir(<name>)`. The package tier SHALL always be reachable so that a missing data directory never raises.

#### Scenario: User override wins
- **WHEN** `templates_path` is set to an existing directory
- **THEN** `settings.template_dir()` returns that directory

#### Scenario: Data directory used when present
- **WHEN** no override is set and `{app}/data/templates/` exists
- **THEN** resolution returns `{app}/data/templates/`

#### Scenario: Falls back to the package
- **WHEN** no override is set and `{app}/data/templates/` does not exist
- **THEN** resolution returns the package `templates` directory and no exception is raised

### Requirement: First-run seeding from the package
The system SHALL copy the contents of the package directories `configs`, `templates` and `sounds` into `{app}/data/<name>/` when, for that name, `settings.json` does not exist **and** `{app}/data/<name>/` does not exist. Each directory SHALL be evaluated independently. Existing files SHALL NEVER be overwritten. Each copy SHALL be recorded in the log. A failure to copy SHALL be logged and SHALL NOT abort startup.

Seeding SHALL run only in frozen builds. A source checkout SHALL read the package directories directly, so that edits under `sportorg/data/` keep taking effect instead of being shadowed by a copy under `data/`.

#### Scenario: A source checkout seeds nothing
- **WHEN** the application is started from a repository checkout
- **THEN** `{app}/data/` and `{app}/logs/` are created but `data/configs`, `data/templates` and `data/sounds` are not, and resolution reads the package directories

#### Scenario: Fresh installation seeds all three
- **WHEN** neither `settings.json` nor any of the three directories exists
- **THEN** all three directories are created and filled from the package

#### Scenario: Existing settings suppress seeding
- **WHEN** `settings.json` exists and `{app}/data/templates/` does not
- **THEN** no seeding occurs and template resolution falls back to the package

#### Scenario: Existing directory is left alone
- **WHEN** `{app}/data/configs/` exists and contains an edited `ranking.txt`
- **THEN** seeding does not run for `configs` and the edited file is untouched

#### Scenario: Copy failure is not fatal
- **WHEN** copying raises `OSError` part-way through
- **THEN** the exception is logged and startup continues

### Requirement: Explicit startup initialisation
The system SHALL provide `sportorg/startup.py` with `init()` performing, in order: `paths.ensure_dirs()`, `configure_logging()`, `paths.seed_if_first_run()`. `SportOrg.pyw` SHALL call `init()` before importing `sportorg.gui.main`. `sportorg/config.py` SHALL NOT create directories or call `logging.config.dictConfig` at import time; the logging configuration SHALL be produced by `build_log_config()` evaluated after `ensure_dirs()`.

#### Scenario: Seeding precedes settings load
- **WHEN** the application starts for the first time
- **THEN** seeding completes before `load_settings()` can write `settings.json`

#### Scenario: Logging targets an existing directory
- **WHEN** `configure_logging()` runs
- **THEN** `{app}/logs/` already exists and file handlers are created successfully

#### Scenario: Importing config creates nothing
- **WHEN** `sportorg.config` is imported by a test or by `builder.py`
- **THEN** no `data/`, `configs/` or `logs/` directory is created

### Requirement: Unwritable program directory reports a comprehensible error
When `{app}` cannot be written, `ensure_dirs()` SHALL catch the `OSError` and raise `PathsError`. `SportOrg.pyw` SHALL catch `PathsError` and display a `QMessageBox` naming the directory and the reason, then exit.

#### Scenario: Read-only install location
- **WHEN** `{app}/data` cannot be created because of permissions
- **THEN** a message box names the path and the application exits without a traceback-only failure

### Requirement: Path settings use an empty-string sentinel
The fields `templates_path` and the nine `source_*_path` fields in `sportorg/settings.py` SHALL default to `""`, meaning "resolve from `{app}`". A non-empty value SHALL be treated as an explicit user override and used verbatim. `sportorg/settings.py` SHALL expose one named accessor per reference file (for example `ranking_score_path()`) that returns the override when set and the resolved default otherwise. The settings dialog SHALL continue to display the resolved effective path.

#### Scenario: Empty resolves from the program directory
- **WHEN** `source_ranking_score_path` is `""` and `{app}/data/configs/ranking.txt` exists
- **THEN** `ranking_score_path()` returns that path

#### Scenario: Override used verbatim
- **WHEN** `source_ranking_score_path` is `D:\shared\ranking.txt`
- **THEN** `ranking_score_path()` returns exactly that value

#### Scenario: Opening the settings dialog does not freeze the default
- **WHEN** the settings dialog is opened and closed without choosing a templates directory
- **THEN** `templates_path` remains `""`

### Requirement: One-time migration of legacy absolute paths
`sportorg/settings.py` SHALL define `settings_version: int = 1` and `CURRENT_SETTINGS_VERSION = 2`. On load, a value below `CURRENT_SETTINGS_VERSION` SHALL trigger migration exactly once, after which `settings_version` SHALL be set to `CURRENT_SETTINGS_VERSION` and the file saved. Migration SHALL clear a path field to `""` only when the stored path does not exist on disk **and** its shape matches a former default: `source_*_path` ending in `configs/<expected-name>.txt`, `source_rent_cards_path` ending in `data/rent_cards.txt`, `templates_path` ending in `sportorg/data/templates` or `templates`.

#### Scenario: Legacy file is migrated
- **WHEN** `settings.json` has no `settings_version` key
- **THEN** migration runs and the file is saved with `settings_version` equal to `2`

#### Scenario: Dead default path is cleared
- **WHEN** `source_countries_path` points at a non-existent `.../configs/countries.txt`
- **THEN** the field is cleared to `""`

#### Scenario: Live path is kept
- **WHEN** `source_countries_path` points at an existing file
- **THEN** the field is unchanged

#### Scenario: Offline user path is kept
- **WHEN** `templates_path` is `\\\\server\\share\\my-templates` and is currently unreachable
- **THEN** the field is unchanged, because its shape does not match a former default

#### Scenario: Migration does not repeat
- **WHEN** the application starts again after a successful migration
- **THEN** `settings_version` is `2` and no path field is examined

### Requirement: Reference tables shipped inside the package
The nine reference files currently in the repository-root `configs/` directory SHALL live in `sportorg/data/configs/`. The root `configs/` directory SHALL be removed. `builder.py` SHALL NOT list `configs` as a separate `include_files` entry.

#### Scenario: Reference tables reach a frozen build
- **WHEN** the application is frozen with `builder.py build`
- **THEN** `lib/sportorg/data/configs/ranking.txt` is present in the build output

### Requirement: Installers pre-create writable directories
Both installers SHALL create `{app}\data` and `{app}\logs` at install time and grant write permission to all users. The Inno Setup script SHALL do this through its `[Dirs]` section with `Permissions: everyone-full`. The MSI SHALL do this through `Directory`, `CreateFolder` and `LockPermissions` rows supplied via `bdist_msi_options["data"]`. Seeded subdirectories SHALL NOT be listed; they are created at first run and inherit the parent permissions.

#### Scenario: Standard user runs an installed build
- **WHEN** the application is installed under `Program Files` and started by a user without administrative rights
- **THEN** it starts, writes to `{app}\logs`, and saves settings to `{app}\data`

### Requirement: Three release artifacts
`release.yml` SHALL produce and attach an MSI, an Inno Setup `.exe` and a portable `.zip` of the frozen build directory. The Inno script SHALL take its version from the CI invocation via `ISCC /D` rather than a hard-coded literal, SHALL target `build\exe.win-amd64-3.8`, SHALL use `{autopf}`, and SHALL NOT reference the 32-bit `AdditionalLib32` payload.

#### Scenario: Tagged release publishes all three
- **WHEN** a `v*` tag is pushed
- **THEN** the release contains a `.msi`, an `.exe` installer and a portable `.zip`

#### Scenario: Portable archive self-initialises
- **WHEN** the portable `.zip` is unpacked into an empty directory and started
- **THEN** `data/`, `data/configs/`, `data/templates/`, `data/sounds/` and `logs/` are created and seeded next to the executable
