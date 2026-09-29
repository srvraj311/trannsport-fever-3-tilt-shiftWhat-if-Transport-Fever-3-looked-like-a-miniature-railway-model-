"""The settings the app shows, their defaults, and saving them between runs.

Defaults are not written here: they are the `const` values in glsl/*.glsl, so the shader files stay the single
source of the approved look and "Reset to defaults" always returns to it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import AUTHOR, shaders


@dataclass(frozen=True)
class Setting:
    key: str                     # TS_ constant name in a snippet, or an app-level switch (lower case)
    label: str
    tab: str
    help: str
    low: float = 0.0
    high: float = 1.0
    step: float = 0.01
    kind: str = "slider"         # slider | check | choice
    choices: tuple = ()          # for kind == "choice": ((value, label), ...)
    unit: str = ""


TABS = ("Blur", "Focus", "Zoom", "Sharp range", "Cab view", "Colour")

SETTINGS: tuple[Setting, ...] = (
    # --- switches for the whole effect (not shader constants) ---
    Setting("enable_tiltshift", "Tilt-shift blur", "Blur", "Blur by distance from the focus point.", kind="check"),
    Setting("enable_colour", "Colour boost", "Colour", "Slightly stronger colours and contrast, like a photographed model.",
            kind="check"),

    # --- Blur ---
    Setting("TS_MAX_BLUR", "Blur size", "Blur", "Largest blur radius, in pixels of a 1080p screen (scales with resolution).",
            0.0, 25.0, 0.25, unit="px"),
    Setting("TS_TAPS", "Quality", "Blur", "Samples per blurred pixel. More is smoother but slower.", kind="choice",
            choices=((24, "Low (24)"), (32, "Medium (32)"), (48, "High (48)"), (64, "Ultra (64)"))),

    # --- Focus ---
    Setting("TS_FOCUS_Y", "Focus point height", "Focus",
            "Where the focus is measured, from the top of the screen (0.5 = centre). Slightly low suits followed vehicles.",
            0.3, 0.8, 0.01),
    Setting("TS_FOCUS_W", "Focus area width", "Focus",
            "Half width of the area the focus is measured over. Larger is steadier, smaller is more precise.", 0.02, 0.5),
    Setting("TS_FOCUS_H", "Focus area height", "Focus", "Half height of that area.", 0.02, 0.4),
    Setting("TS_FOCUS_NEAR_BIAS", "Near-object priority", "Focus",
            "How strongly nearer things win the focus (0 = plain average). Keeps a vehicle in front of a field sharp.",
            0.0, 4.0, 0.1),

    # --- Zoom dependency ---
    Setting("TS_ZOOM_CLOSE", "Close-up distance", "Zoom",
            "Focus at or closer than this uses the close-up values (vehicle follow, street level).", 5, 300, 5, unit="m"),
    Setting("TS_ZOOM_FAR", "Zoomed-out distance", "Zoom",
            "Focus at or beyond this uses the zoomed-out values. In between, the two blend smoothly.", 50, 2000, 10,
            unit="m"),
    Setting("TS_AMOUNT_CLOSE", "Strength close up", "Zoom", "Overall blur strength when zoomed in.", 0.0, 1.5),
    Setting("TS_AMOUNT_FAR", "Strength zoomed out", "Zoom", "Overall blur strength when zoomed out.", 0.0, 1.5),

    # --- Sharp range (in doublings of distance: 1.0 = twice as far, or half as far, as the focus) ---
    Setting("TS_CLOSE_NEAR_SHARP", "Close up: sharp in front", "Sharp range",
            "How far in front of the focus stays sharp (1.0 = down to half the focus distance).", 0.0, 3.0, 0.05),
    Setting("TS_CLOSE_NEAR_RAMP", "Close up: blur build-up in front", "Sharp range",
            "How gradually blur grows after that (bigger = softer).", 0.1, 4.0, 0.05),
    Setting("TS_CLOSE_FAR_SHARP", "Close up: sharp behind", "Sharp range",
            "How far behind the focus stays sharp (1.0 = up to twice the focus distance).", 0.0, 3.0, 0.05),
    Setting("TS_CLOSE_FAR_RAMP", "Close up: blur build-up behind", "Sharp range", "How gradually blur grows after that.",
            0.1, 4.0, 0.05),
    Setting("TS_FAR_NEAR_SHARP", "Zoomed out: sharp in front", "Sharp range", "As above, for the zoomed-out view.",
            0.0, 3.0, 0.05),
    Setting("TS_FAR_NEAR_RAMP", "Zoomed out: blur build-up in front", "Sharp range", "", 0.1, 4.0, 0.05),
    Setting("TS_FAR_FAR_SHARP", "Zoomed out: sharp behind", "Sharp range", "", 0.0, 3.0, 0.05),
    Setting("TS_FAR_FAR_RAMP", "Zoomed out: blur build-up behind", "Sharp range", "", 0.1, 4.0, 0.05),

    # --- Cab view ---
    Setting("TS_CAB_ENABLED", "Sharp lower screen in cab view", "Cab view",
            "When the camera looks almost level and close (cab view), keep the lower part of the screen sharp.",
            kind="check"),
    Setting("TS_CAB_SPLIT", "Sharp below", "Cab view", "Screen height (from the top) below which blur is removed.",
            0.2, 0.9),
    Setting("TS_CAB_SOFT", "Edge softness", "Cab view", "Width of the soft edge around that line.", 0.0, 0.2),

    # --- Colour ---
    Setting("TS_SATURATION", "Saturation", "Colour", "Extra colour saturation.", 0.0, 0.5),
    Setting("TS_CONTRAST", "Contrast", "Colour", "Extra contrast.", 0.0, 0.3),
)

BY_KEY = {s.key: s for s in SETTINGS}
APP_SWITCHES = ("enable_tiltshift", "enable_colour")


def defaults() -> dict[str, float]:
    values: dict[str, float] = {key: 1.0 for key in APP_SWITCHES}
    for name in ("ssr_tiltshift.glsl", "compose_grade.glsl"):
        values.update(shaders.read_constants(shaders.snippet(name)))
    return {s.key: values[s.key] for s in SETTINGS}


def clamp(setting: Setting, value: float) -> float:
    if setting.kind == "check":
        return 1.0 if value else 0.0
    if setting.kind == "choice":
        options = [v for v, _ in setting.choices]
        return float(min(options, key=lambda v: abs(v - value)))
    return min(max(float(value), setting.low), setting.high)


def config_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / AUTHOR / "TF3TiltShift" / "settings.json"


def load() -> tuple[dict[str, float], str | None]:
    """Saved settings over the defaults, and the saved game folder (or None)."""
    values = defaults()
    game_dir = None
    try:
        saved = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return values, None
    for key, value in saved.get("values", {}).items():
        if key in BY_KEY and isinstance(value, (int, float)):
            values[key] = clamp(BY_KEY[key], value)
    if isinstance(saved.get("game_dir"), str):
        game_dir = saved["game_dir"]
    return values, game_dir


def save(values: dict[str, float], game_dir: str | None) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"values": values, "game_dir": game_dir}, indent=2), encoding="utf-8")
