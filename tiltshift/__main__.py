"""Entry point.

    python -m tiltshift            # open the app
    python -m tiltshift apply      # patch the game with the saved settings (or the defaults)
    python -m tiltshift restore    # put the game's original shaders back
    python -m tiltshift probe      # diagnostic tint (red/blue/green) to check the shaders still load after a game update
"""
from __future__ import annotations

import sys
from pathlib import Path

from tiltshift import game, settings, shaders


def cli(command: str) -> int:
    values, saved_dir = settings.load()
    path = Path(saved_dir) if saved_dir and game.is_game_dir(Path(saved_dir)) else game.find_game()
    if path is None:
        print("Transport Fever 3 not found; open the app once and pick the folder with Browse...", file=sys.stderr)
        return 2
    try:
        if command == "restore":
            done = game.restore_all(path)
        else:
            done = game.apply(path, values, probe=command == "probe")
    except shaders.PatchError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{path}: " + (", ".join(done) or "nothing to do"))
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] not in ("apply", "restore", "probe"):
            print(__doc__, file=sys.stderr)
            return 2
        return cli(sys.argv[1])
    from tiltshift.app import main as run_app
    run_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
