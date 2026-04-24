"""solo-campaign: scaffold a new solo RPG campaign folder."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-campaign",
                                     description="Scaffold a new solo RPG campaign folder.")
    parser.add_argument("name", help="Display name for the campaign")
    parser.add_argument("path", help="Target campaign directory (must not exist)")
    parser.add_argument("--vault", type=str, default=None,
                        help="Player Obsidian vault path")
    parser.add_argument("--skills-dir", type=str, default=None,
                        help="Override ~/.claude/skills/ (env: CLAUDE_SKILLS_DIR)")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
