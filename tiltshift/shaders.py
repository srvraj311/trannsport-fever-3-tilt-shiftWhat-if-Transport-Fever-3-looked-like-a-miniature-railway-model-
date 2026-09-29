"""Turn the game's original shader source plus our settings into patched shader source.

Nothing here touches the disk except reading our own snippets (glsl/*.glsl, shipped with the app).
Every patch anchor must match exactly once; if a game update changes a file, PatchError says so instead of
writing a broken shader.
"""
from __future__ import annotations

import re
from pathlib import Path

SNIPPETS = Path(__file__).resolve().parent / "glsl"
MARKER = "srvraj311_tiltshift"          # present in every patched file; tells patched and original files apart

# `const float TS_NAME = value;` (or int) lines in our snippets: the values the app's settings replace.
_CONST = re.compile(r"^(const\s+(float|int)\s+(TS_\w+)\s*=\s*)([^;]+)(;)", re.MULTILINE)


class PatchError(Exception):
    pass


def snippet(name: str) -> str:
    return (SNIPPETS / name).read_text(encoding="utf-8").replace("\r\n", "\n")


def read_constants(text: str) -> dict[str, float]:
    """{name: value} of every TS_ constant in a snippet (these are the defaults)."""
    return {m.group(3): float(m.group(4)) for m in _CONST.finditer(text)}


def glsl_number(value: float, kind: str) -> str:
    if kind == "int":
        return str(int(round(value)))
    text = f"{value:.4f}".rstrip("0")
    return text + "0" if text.endswith(".") else text        # "400." -> "400.0": GLSL wants a digit after the dot


def set_constants(text: str, values: dict[str, float]) -> str:
    """Replace the value of each TS_ constant that appears in values; leave the rest as written."""
    def repl(m: re.Match) -> str:
        name = m.group(3)
        if name not in values:
            return m.group(0)
        return m.group(1) + glsl_number(values[name], m.group(2)) + m.group(5)
    return _CONST.sub(repl, text)


def _replace_once(text: str, old: str, new: str, what: str) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{what}: expected the game's shader to contain {old.strip()!r} once, found {count}. "
                         "The game was probably updated; this version of the app does not know the new shader.")
    return text.replace(old, new)


def patch_compose(original: str, values: dict[str, float]) -> str:
    """Colour boost: grade the final image just before the game writes it out."""
    text = _replace_once(original, "void main() {", set_constants(snippet("compose_grade.glsl"), values) + "void main() {",
                         "compose.fs")
    return _replace_once(text, "\tcolor.rgb = col;", "\tcol = tsGrade(col);\n\tcolor.rgb = col;", "compose.fs")


def patch_ssr(original: str, values: dict[str, float], probe: bool = False) -> str:
    """Tilt-shift: rename the game's main() and append ours, which calls it first and then blurs by distance."""
    text = _replace_once(original, "void main() {", "void ssrMain() {", "ssr_apply.fs")
    extra = snippet("ssr_probe.glsl") if probe else set_constants(snippet("ssr_tiltshift.glsl"), values)
    return text.rstrip("\n") + "\n" + extra
