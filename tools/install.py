"""Patch the built shaders into Transport Fever 3's own files (or restore the originals).

    python tools/install.py              # patch the game (refuses while the game is running)
    python tools/install.py --restore    # put the original shaders back
    python tools/install.py --dry-run
    python tools/install.py --live       # allow while the game runs; then press Right Alt + T in game to reload shaders

TF3 loads its shaders from base/content only (::/rendering/..., compiled at start-up before any mod is mounted), so a mod folder's
content/ cannot replace them; that was tested with the probe build on 2026-09-30. Instead each patched file is written over the
game's copy, and the untouched original is kept beside it as <name>.tiltshift_orig (made once, never overwritten). A game update or
Steam's "verify integrity" restores the originals; re-run build + install afterwards.
The old mod-folder install (<userdata>/3493540/local/mods/srvraj311_tiltshift) did nothing and is removed when found.
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import BACKUP_SUFFIX, COMPOSE, GAME, MOD_ID, SSR  # noqa: E402

TARGETS = (COMPOSE, SSR)
OLD_MOD_DIRS = rf"C:\Program Files (x86)\Steam\userdata\*\3493540\local\mods\{MOD_ID}"


def game_running() -> bool:
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True, check=False).stdout
    except OSError:
        return False
    return "transportfever3" in out.lower()


def restore(rel: str, dry: bool) -> None:
    live = GAME / "base" / "content" / rel
    backup = live.with_name(live.name + BACKUP_SUFFIX)
    if backup.is_file():
        print(f"[install] restore {live}")
        if not dry:
            shutil.copy2(backup, live)
            backup.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--live", action="store_true", help="patch while the game runs (only shader text files change)")
    a = ap.parse_args()
    built = REPO / "build" / "mod" / MOD_ID
    if not a.restore and not built.is_dir():
        print("[install] nothing built; run tools/build.py first", file=sys.stderr)
        return 2
    if game_running() and not (a.dry_run or a.live):
        print("[install] Transport Fever 3 is running; close it first, or use --live and press Right Alt + T", file=sys.stderr)
        return 3

    for old in glob.glob(OLD_MOD_DIRS):
        print(f"[install] remove old mod folder {old}")
        if not a.dry_run:
            shutil.rmtree(old)

    if a.restore:
        for rel in TARGETS:
            restore(rel, a.dry_run)
        return 0

    variant = (built / "variant.txt").read_text().strip()
    for rel in TARGETS:
        src = built / "content" / rel
        if not src.is_file():          # e.g. the simple variant leaves ssr_apply.fs alone
            restore(rel, a.dry_run)
            continue
        live = GAME / "base" / "content" / rel
        backup = live.with_name(live.name + BACKUP_SUFFIX)
        print(f"[install] {variant}: patch {live}")
        if a.dry_run:
            continue
        if not backup.exists():
            shutil.copy2(live, backup)
        shutil.copyfile(src, live)     # new modification time, so the game's shader cache recompiles it
    return 0


if __name__ == "__main__":
    sys.exit(main())
