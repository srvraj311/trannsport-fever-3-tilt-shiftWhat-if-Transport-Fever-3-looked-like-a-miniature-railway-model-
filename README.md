# TF3 Tilt-Shift

A Cities: Skylines-style **tilt-shift / depth-of-field** look for **Transport Fever 3**, with a small settings app.

The focus point is found automatically and prefers the nearest object, such as the train you follow. Things in front of or
behind it blur more the further they are from it. The sharp range follows the zoom, and a slight colour boost gives the
"photographed model" feel. By [srvraj311](https://github.com/srvraj311).

## Use

1. Download `TF3TiltShift.exe` from the Releases page and run it. No install is needed.
2. It finds Transport Fever 3 in your Steam libraries. If it doesn't, use **Browse...** to pick the game folder.
3. Adjust the settings if you like, then press **Apply to game**.
4. In game, press **Right Alt + T** to reload shaders, or just start the game.

**Restore original shaders** puts the game's own files back. **Reset to defaults** returns every slider to the default
look. Turn on **Apply automatically** to see changes live: move a slider, then press Right Alt + T in game.

Settings are saved to `%APPDATA%\srvraj311\TF3TiltShift\settings.json`.

| Tab | Settings |
|---|---|
| Blur | on/off, blur size, quality (samples per pixel) |
| Focus | where the focus is measured, the size of that area, how strongly near objects win it |
| Zoom | the distances counted as "close up" and "zoomed out", and the strength at each |
| Sharp range | how far in front of and behind the focus stays sharp, and how gradually blur builds up, for close-up and zoomed-out views |
| Cab view | keep the lower screen sharp when the camera looks level and close (cab view) |
| Colour | colour boost on/off, saturation, contrast |

## Good to know

- **It is not a Mod Hub mod.** TF3 loads its shaders only from its own install folder, and a mod folder cannot replace
  them, which was tested in game. The app edits two of the game's post-process shaders instead:
  `base/content/rendering/programs/shaders/hdr/compose.fs` and `.../misc/ssr_apply.fs`. Each original is kept beside
  it as `*.tiltshift_orig`.
- **Game updates and Steam "Verify integrity"** put the original shaders back. Open the app and press **Apply to game**
  again. If an update changed those shaders in a way the app doesn't know, it refuses to apply and says so, instead of
  writing a broken shader.
- **Works with screen-space reflections on or off.** Menus and other UI are never blurred.
- **Other shader tweaks** that edit the same two files will conflict.
- **No game code is shipped.** The app contains only its own GLSL snippets. It reads your installed game's shaders and
  patches them on your PC.
- **Motion blur isn't possible.** The engine gives these shaders no motion data and no memory of earlier frames.

## How it works

- `ssr_apply.fs`, a full-screen pass that has the depth buffer: the game's `main()` is renamed `ssrMain()`, and our
  `main()` runs it, then blurs.
  - **Focus**: a near-weighted average distance over 63 points in a patch just below the screen centre, ignoring sky.
    It stays steady when a pole or wire passes through.
  - **Blur amount**: by distance only, as `log2(distance / focus)`, so it scales with the zoom. There are separate near
    and far ranges, like CS2's Near/Far Start/End, blended between close-up and zoomed-out values.
  - **Gather**: 48 taps at fixed screen offsets, so nothing shimmers while the blur changes. Taps sharper than the pixel
    are ignored, so there are no halos around sharp objects.
- `compose.fs`, the final tone-mapping pass: the colour boost.

The defaults are the `const` values in [tiltshift/glsl/](tiltshift/glsl/). The app rewrites those values from its
settings.

## From source

Needs Python 3.10+ on Windows. No packages are needed to run it; building the .exe needs PyInstaller.

```
python -m tiltshift                          # the app
python -m tiltshift apply | restore | probe  # without the window; probe = coloured test to check the shaders still load
python -m unittest discover -s tests -t .    # tests (no game needed)
python -m pip install pyinstaller
python tools/build_exe.py                    # -> dist/TF3TiltShift.exe
```

To publish a release, push a version tag (for example `git tag v1.0.1 && git push origin v1.0.1`). The
[Release workflow](.github/workflows/release.yml) runs the tests, builds the single-file `TF3TiltShift.exe` and attaches
it to a GitHub Release.

- [tiltshift/app.py](tiltshift/app.py): the window
- [tiltshift/settings.py](tiltshift/settings.py): the list of settings and saving them
- [tiltshift/shaders.py](tiltshift/shaders.py): builds the patched shader text
- [tiltshift/game.py](tiltshift/game.py): finds the game, applies and restores with backups

## Licence

MIT, see [LICENSE](LICENSE). Transport Fever 3 and its shaders belong to Urban Games; this project ships none of them.
