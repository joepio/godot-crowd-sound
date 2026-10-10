#!/usr/bin/env python3
"""Copy the crowd_sound addon into a Godot game, or check that its copy matches.

Godot has no package manager, so each game vendors `addons/crowd_sound`. Run
this from a checkout of this repository after changing the addon:

    python sync.py path/to/game            # update the game's copy
    python sync.py --check path/to/game    # fail if the copy differs

Everything under `addons/crowd_sound` is copied, samples included. A game's own
`.uid` files are kept, because its scripts may refer to them.
"""
import argparse
import shutil
import sys
from pathlib import Path

ADDON = Path(__file__).resolve().parent / "addons" / "crowd_sound"


def addon_files() -> list[str]:
    return sorted(str(p.relative_to(ADDON)) for p in ADDON.rglob("*")
                  if p.is_file() and p.suffix != ".uid")


def sync(game: Path, check: bool) -> list[str]:
    if not (game / "project.godot").is_file():
        return [f"{game}: not a Godot project (no project.godot)"]
    target_dir = game / "addons" / "crowd_sound"
    problems = []
    for name in addon_files():
        source, target = ADDON / name, target_dir / name
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        if check:
            state = "missing" if not target.exists() else "differs from godot-crowd-sound"
            problems.append(f"{target}: {state}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        uid = ADDON / f"{name}.uid"
        if uid.exists() and not (target_dir / f"{name}.uid").exists():
            shutil.copyfile(uid, target_dir / f"{name}.uid")
        print(f"updated {target}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("games", nargs="+", type=Path, help="Godot project directories")
    parser.add_argument("--check", action="store_true", help="only report differences")
    args = parser.parse_args()
    problems = [p for game in args.games for p in sync(game, args.check)]
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print("crowd_sound matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
