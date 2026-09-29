# Tilt-Shift Miniature (Transport Fever 3)

A visual mod that gives TF3 a Cities: Skylines-style "miniature" look. The effect is a shallow depth of field centred on whatever
is in the middle of the screen, plus a small colour boost.

## How it works

TF3 compiles its GLSL shaders from `base/content/rendering/programs` on start (see `local/shader_cache/cache.lua`). It always
reads them from the base game, so a mod folder cannot replace them: the probe build proved this on 2026-09-30. `tools/install.py`
therefore writes patched copies of two full-screen passes over the game's own files. The originals are kept beside them as
`*.tiltshift_orig`, and `python tools/install.py --restore` puts them back. A game update or Steam's "verify integrity" also
restores them; re-run the build and install afterwards.

| File | Receives from the engine | We add |
|---|---|---|
| `shaders/misc/ssr_apply.fs` | lit scene, **depth buffer**, camera matrices | distance-based tilt-shift blur (`shaders/ssr_tiltshift.glsl`) |
| `shaders/hdr/compose.fs` | lit scene + bloom (final tone mapping) | colour boost; in the `simple` variant also the band blur |

The base files are **not** stored here. `tools/build.py` reads them from the game and applies small text patches. Each patch
anchor must match exactly once, so a game update that changes a file stops the build instead of producing broken shaders.

Motion blur is not possible this way. The engine gives shaders no motion data and no record of the previous frame, and a mod
cannot add new shader inputs.

## Variants

```
python tools/build.py probe    # test: left third red (compose runs), middle third blue with distance (depth reads), right third green (ssr_apply runs)
python tools/build.py depth    # the real mod
python tools/build.py simple   # fallback when ssr_apply does not run: screen-band blur, no depth
python tools/install.py        # patch the game's shaders (game must be closed)
python tools/install.py --restore
```

## Tuning

The settings are the `const float TS_*` values at the top of `shaders/ssr_tiltshift.glsl` and `shaders/compose_functions.glsl`.
To tune while the game runs, edit the patched files under `Transport Fever 3/base/content/rendering/programs/shaders/` and press
**Right Alt + T**, the game's debug "reload shaders" key. Copy good values back here afterwards.

Shader errors are logged in `local/crash_dump/stdout.txt`.

## Status

Working in game (2026-09-30, reflections off). The tuned look is saved in `shaders/ssr_tiltshift.glsl`:
- focus: a near-weighted average over a patch below the screen centre
- blur: by distance only, using Cities: Skylines II-style near/far ranges that follow the zoom
- flicker: taps at fixed screen offsets, no halos
- cab view: the bottom half stays sharp

The probe build and the `simple` variant are kept for diagnosing a future game update.
