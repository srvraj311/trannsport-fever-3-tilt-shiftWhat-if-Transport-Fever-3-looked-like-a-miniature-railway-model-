"""Build dist/TF3TiltShift.exe (one file, no console) with PyInstaller.

    python -m pip install pyinstaller
    python tools/build_exe.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from tiltshift import APP_NAME, AUTHOR, __version__  # noqa: E402

BUILD = REPO / "build"
VERSION_FILE = BUILD / "version_info.txt"


def write_version_info() -> None:
    """Windows file properties (Details tab): product, version, owner."""
    nums = tuple(int(n) for n in __version__.split(".")) + (0,)
    strings = {
        "CompanyName": AUTHOR,
        "FileDescription": APP_NAME,
        "FileVersion": __version__,
        "InternalName": "TF3TiltShift",
        "LegalCopyright": f"(c) {AUTHOR}",
        "OriginalFilename": "TF3TiltShift.exe",
        "ProductName": APP_NAME,
        "ProductVersion": __version__,
    }
    entries = ",\n".join(f"          StringStruct('{k}', '{v}')" for k, v in strings.items())
    BUILD.mkdir(exist_ok=True)
    VERSION_FILE.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}),
  kids=[
    StringFileInfo([StringTable('040904B0', [
{entries}
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")


def main() -> int:
    write_version_info()
    return subprocess.call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "TF3TiltShift",
        "--add-data", f"{REPO / 'tiltshift' / 'glsl'};tiltshift/glsl",
        "--version-file", str(VERSION_FILE),
        "--distpath", str(REPO / "dist"), "--workpath", str(BUILD / "pyinstaller"), "--specpath", str(BUILD),
        str(REPO / "run_app.py"),
    ])


if __name__ == "__main__":
    sys.exit(main())
