"""Find Transport Fever 3 and patch or restore its two post-process shaders.

TF3 always loads its shaders from its own base/content folder (a mod folder cannot replace them), so the patched
files are written over the game's copies. The untouched original is kept beside each one as <name>.tiltshift_orig.
Rules:
- A live file WITHOUT our marker is an original (first run, or the game was updated / verified): it becomes the backup.
- A live file WITH our marker is ours: the backup is the original to patch from.
- Restore copies the backup back and deletes it.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import shaders

GAME_FOLDER = "Transport Fever 3"
GAME_EXE = "TransportFever3.exe"
SHADER_ROOT = Path("base", "content", "rendering", "programs", "shaders")
COMPOSE = SHADER_ROOT / "hdr" / "compose.fs"
SSR = SHADER_ROOT / "misc" / "ssr_apply.fs"
BACKUP_SUFFIX = ".tiltshift_orig"


def is_game_dir(path: Path) -> bool:
    return (path / GAME_EXE).is_file() and (path / COMPOSE).is_file() and (path / SSR).is_file()


def _steam_roots() -> list[Path]:
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            roots.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
    except OSError:
        pass
    roots += [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    return roots


def find_game() -> Path | None:
    """Look through every Steam library listed in libraryfolders.vdf."""
    libraries = []
    for root in _steam_roots():
        vdf = root / "steamapps" / "libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        libraries.append(root)
        libraries += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    for library in libraries:
        candidate = library / "steamapps" / "common" / GAME_FOLDER
        if is_game_dir(candidate):
            return candidate
    return None


def is_running() -> bool:
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}"], capture_output=True, text=True,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except OSError:
        return False
    return GAME_EXE.lower() in out.lower()


def _backup(live: Path) -> Path:
    return live.with_name(live.name + BACKUP_SUFFIX)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def original_text(game: Path, rel: Path) -> str:
    """The game's own version of a shader, refreshing the backup when the live file is an original."""
    live = game / rel
    text = _read(live)
    if shaders.MARKER not in text:
        shutil.copy2(live, _backup(live))
        return text
    if not _backup(live).is_file():
        raise shaders.PatchError(f"{live.name} is patched but its backup is missing. In Steam, use "
                                 "Properties > Installed Files > Verify integrity, then apply again.")
    return _read(_backup(live))


def is_patched(game: Path, rel: Path) -> bool:
    return shaders.MARKER in _read(game / rel)


def restore(game: Path, rel: Path) -> bool:
    live = game / rel
    backup = _backup(live)
    if not backup.is_file():
        return False
    if is_patched(game, rel):
        shutil.copyfile(backup, live)   # copyfile gives a new modification time, so the game recompiles the shader
    backup.unlink()
    return True


def apply(game: Path, values: dict[str, float], probe: bool = False) -> list[str]:
    """Patch (or restore) both shaders to match the settings. Returns what was done, one line each."""
    done = []
    plan = [(COMPOSE, bool(values["enable_colour"]) and not probe, shaders.patch_compose),
            (SSR, bool(values["enable_tiltshift"]) or probe,
             lambda original, v: shaders.patch_ssr(original, v, probe=probe))]
    patched = {}
    for rel, wanted, patch in plan:                 # build everything first, so a PatchError writes nothing
        if wanted:
            patched[rel] = patch(original_text(game, rel), values)
    for rel, wanted, _ in plan:
        if wanted:
            with open(game / rel, "w", encoding="utf-8", newline="\n") as f:
                f.write(patched[rel])
            done.append(f"patched {rel.name}")
        elif restore(game, rel):
            done.append(f"restored {rel.name}")
    return done


def restore_all(game: Path) -> list[str]:
    return [f"restored {rel.name}" for rel in (COMPOSE, SSR) if restore(game, rel)]
