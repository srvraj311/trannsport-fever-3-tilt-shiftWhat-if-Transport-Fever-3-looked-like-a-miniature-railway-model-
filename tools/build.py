"""Build the tilt-shift mod by patching the installed game's own post-process shaders.

    python tools/build.py probe     # test build: red / blue / green thirds show which passes run and that depth reads
    python tools/build.py depth     # depth-aware tilt-shift (shaders/misc/ssr_apply.fs) + colour boost (shaders/hdr/compose.fs)
    python tools/build.py simple    # fallback: screen-band tilt-shift + colour boost, compose.fs only

The repo holds only our GLSL (shaders/*.glsl) and these patch rules; the base shaders are read from the game at build time, so a
game update is picked up by rebuilding. Every patch anchor must match exactly once, or the build stops (the game changed the file).
Output: build/mod/srvraj311_tiltshift (install with tools/install.py).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_ID = "srvraj311_tiltshift"
GAME = Path(os.environ.get("TF3_GAME_DIR", r"E:\SteamLibrary\steamapps\common\Transport Fever 3"))
SHADERS = "rendering/programs/shaders"
COMPOSE = f"{SHADERS}/hdr/compose.fs"
SSR = f"{SHADERS}/misc/ssr_apply.fs"

NAMES = {
    "probe": "Tilt-Shift Miniature (probe)",
    "depth": "Tilt-Shift Miniature",
    "simple": "Tilt-Shift Miniature (simple)",
}


BACKUP_SUFFIX = ".tiltshift_orig"   # tools/install.py --game keeps the untouched original next to the patched file


def base_shader(rel: str) -> str:
    path = GAME / "base" / "content" / rel
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.is_file():
        path = backup
    if not path.is_file():
        sys.exit(f"[build] base shader not found: {path} (set TF3_GAME_DIR)")
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if "srvraj311_tiltshift" in text:
        sys.exit(f"[build] {path} is already patched and has no {BACKUP_SUFFIX} backup; verify the game files in Steam")
    return text


def snippet(name: str) -> str:
    return (REPO / "shaders" / name).read_text(encoding="utf-8").replace("\r\n", "\n")


def replace_once(text: str, old: str, new: str, what: str) -> str:
    n = text.count(old)
    if n != 1:
        sys.exit(f"[build] {what}: expected 1 match for {old.strip()!r}, found {n}; the game's shader changed, update the patch")
    return text.replace(old, new)


def patch_compose(variant: str) -> str:
    src = base_shader(COMPOSE)
    src = replace_once(src, "void main() {", snippet("compose_functions.glsl") + "void main() {", "compose: functions")
    out = "\tcolor.rgb = col;"
    if variant == "probe":
        # Left third red = compose.fs replacement is loaded.
        src = replace_once(src, out, out + "\n\tif (texCoord2.x < 0.333) {\n\t\tcolor.rgb *= vec3(1.0, 0.55, 0.55);\n\t}",
                           "compose: probe")
        return src
    if variant == "simple":
        sample = "vec3 col = texture(texFramebuf, texCoord2.xy).rgb;"
        src = replace_once(src, sample, "vec3 col = tsBandBlur(texCoord2.xy);", "compose: band blur")
    return replace_once(src, out, "\tcol = tsGrade(col);\n" + out, "compose: colour boost")


def patch_ssr(variant: str) -> str:
    src = base_shader(SSR)
    src = replace_once(src, "void main() {", "void ssrMain() {", "ssr_apply: rename main")
    return src.rstrip("\n") + "\n" + snippet("ssr_probe.glsl" if variant == "probe" else "ssr_tiltshift.glsl")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant", choices=sorted(NAMES))
    a = ap.parse_args()

    out = REPO / "build" / "mod" / MOD_ID
    if out.exists():
        shutil.rmtree(out)
    content = out / "content"
    write(content / COMPOSE, patch_compose(a.variant))
    if a.variant != "simple":
        write(content / SSR, patch_ssr(a.variant))

    write(out / "mod.json", json.dumps({
        "modId": MOD_ID,
        "revision": 1,
        "severityAdd": "None",
        "severityRemove": "None",
        "visible": True,
        "cosmetic": True,
        "dependencies": None,
        "incompatibilities": None,
    }, indent=4) + "\n")
    write(out / "_metadata" / "modinfo.json", json.dumps({
        "name": NAMES[a.variant],
        "summary": "Miniature look: tilt-shift blur around the point you look at, plus a slight colour boost.",
        "description": (REPO / "mod" / "description.txt").read_text(encoding="utf-8").strip(),
        "authors": [{"name": "srvraj311", "role": "CREATOR"}],
        "tags": [],
        "dependencies": [],
        "url": "",
    }, indent=4) + "\n")
    write(out / "variant.txt", a.variant + "\n")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    print(f"[build] {a.variant}: {out}\n  " + "\n  ".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
