import sys
from importlib.util import find_spec

from cx_Freeze import Executable, setup

from sportorg import config

base = None
if sys.platform == "win32":
    base = "Win32GUI"

include_files = [
    (config.base_dir("sportorg", "data"), "lib/sportorg/data"),
    config.base_dir("LICENSE"),
    config.base_dir("changelog.md"),
    config.base_dir("changelog_ru.md"),
    config.COMMIT_VERSION_FILE,
]
includes = ["atexit", "codecs", "playsound3", "pyImpinj"]
if find_spec("sportorg_rust_example") is not None:
    includes.append("sportorg_rust_example")
if find_spec("sportorg_core") is not None:
    includes.append("sportorg_core")
excludes = ["Tkinter", "unittest", "test", "pydoc"]

build_exe_options = {
    "includes": includes,
    "excludes": excludes,
    "packages": ["idna", "requests", "encodings", "asyncio", "pywinusb"],
    "include_files": include_files,
    "zip_include_packages": ["PySide6"],
    "optimize": 2,
    "include_msvcr": True,
    "silent": 1,
}

# SportOrg stores its races, settings and logs next to the executable, so an
# operator without administrative rights has to be able to write there.  The
# installer creates both directories and grants Everyone full control; MSI
# maps the name "Everyone" to the well-known SID itself, so this also works on
# a localised Windows.
GENERIC_ALL = 0x10000000
WRITABLE_DIRS = [
    ("DataDir", "data"),
    ("LogDir", "logs"),
]

# Identifies the product across releases so that installing a new version
# removes the old one instead of registering a second entry beside it.  This
# GUID is product identity: generated once, it must never change again, or
# every already-installed copy becomes un-upgradable.  It is deliberately not
# the AppId from sportorg.iss -- Inno keeps its own uninstall registry and the
# two never consult each other.
#
# ProductCode stays random per build, which is what a major upgrade requires.
UPGRADE_CODE = "{D652DEE1-13E6-4D7A-B8FC-334FF475E5FD}"

bdist_msi_options = {
    "all_users": True,
    "upgrade_code": UPGRADE_CODE,
    "initial_target_dir": r"[ProgramFiles64Folder]\{}".format(config.NAME),
    "data": {
        "Directory": [(logical, "TARGETDIR", name) for logical, name in WRITABLE_DIRS],
        "CreateFolder": [(logical, "TARGETDIR") for logical, _ in WRITABLE_DIRS],
        "LockPermissions": [
            (logical, "CreateFolder", None, "Everyone", GENERIC_ALL)
            for logical, _ in WRITABLE_DIRS
        ],
        "Shortcut": [
            (
                "DesktopShortcut",  # Shortcut
                "DesktopFolder",  # Directory
                config.NAME,  # Name
                "TARGETDIR",  # Component
                "[TARGETDIR]SportOrg.exe",  # Target
                None,  # Arguments
                None,  # Description
                None,  # Hotkey
                None,  # Icon
                None,  # IconIndex
                None,  # ShowCmd
                "TARGETDIR",  # WkDir
            ),
        ],
    },
}

options = {"build_exe": build_exe_options, "bdist_msi": bdist_msi_options}

executables = [
    Executable(
        "SportOrg.pyw",
        base=base,
        icon=config.icon_dir("sportorg.ico"),
        copyright="GNU GENERAL PUBLIC LICENSE {}".format(config.NAME),
    )
]

setup(
    name=config.NAME,
    version=config.VERSION,
    description=config.NAME,
    options=options,
    executables=executables,
)
