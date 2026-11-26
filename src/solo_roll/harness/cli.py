"""solo-harness: create a demo campaign, or serve a campaign to the browser."""
import argparse
import json
import os
import random
import socket
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from ..rng import RandomDice, ScriptedDice
from .campaign import CampaignPaths, create_campaign
from .demo import DEMO_MAP, DEMO_PARTY, DEMO_START
from .engine import open_campaign
from .errors import HarnessError
from .library import Library
from .. import OSE_DATA_DIR
from ..flextale_import import default_output_dir
from .plugins import builtin_plugins
from .registry import PluginFactory

__all__ = ["main", "lan_ip"]

DEFAULT_PORT = 8765
BIND_HOST = "0.0.0.0"


def lan_ip() -> str:
    """Return the address of the interface that routes off this machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            # A UDP connect sends no packet; it only picks the outgoing interface.
            probe.connect(("10.255.255.255", 1))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def _uvicorn_run(app, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


def _load_script(args) -> dict:
    if not args.script:
        raise HarnessError("--referee scripted needs --script FILE")
    return json.loads(Path(args.script).read_text())


def _serve(
    args, run: Callable, find_ip: Callable[[], str], plugins: Mapping[str, PluginFactory], web_dist: Path
) -> int:
    from .server import create_app

    if not args.campaign and not args.campaigns:
        raise HarnessError("give a campaign folder, or --campaigns for a folder of campaigns")

    script = _load_script(args) if args.referee == "scripted" else {}
    turns = script.get("referee", [])

    def make_referee(engine, paths):
        if args.referee == "scripted":
            from .referee.scripted import ScriptedReferee, turns_from_json

            return ScriptedReferee(engine, paths, turns_from_json(turns))
        if args.referee != "sdk":
            return None
        from .referee import sdk

        for key in ("model", "effort"):
            if getattr(args, key) is not None:
                engine.change_setting("referee", key, getattr(args, key))
        chosen = engine.settings()["referee"]
        return sdk.AgentSdkReferee(engine, paths, model=chosen["model"], effort=chosen["effort"])

    seeds = random.Random(args.seed)

    scripted_dice = ScriptedDice(script["dice"]) if "dice" in script else None

    def dice():
        if scripted_dice is not None:
            return scripted_dice
        return RandomDice(seed=seeds.getrandbits(64))

    engine = referee = library = None
    if args.campaign:
        engine = open_campaign(Path(args.campaign), dice(), plugins)
        referee = make_referee(engine, CampaignPaths(Path(args.campaign)))
    if args.campaigns:
        library = Library(Path(args.campaigns), plugins, dice=dice, referee_factory=make_referee)
    print(f"Harness for {args.campaign or args.campaigns}: http://{find_ip()}:{args.port}/", flush=True)
    run(create_app(engine, web_dist=web_dist, referee=referee, library=library), host=BIND_HOST, port=args.port)
    return 0


def _demo(args) -> int:
    root = create_campaign(
        Path(args.campaign), plugins=["ose", "flextale"], map_data=DEMO_MAP, start=DEMO_START, party=DEMO_PARTY
    )
    print(f"Demo campaign created at {root}. Run: solo-harness serve {root}")
    return 0


def main(
    argv: list[str] | None = None,
    run: Callable | None = None,
    lan_ip: Callable[[], str] = lan_ip,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="solo-harness")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="serve a campaign on the LAN")
    serve.add_argument("campaign", nargs="?", help="a campaign folder to open at start")
    serve.add_argument("--campaigns", default=None,
                       help="a folder of campaigns: the browser can create and open campaigns in it")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--seed", type=int, default=None,
                       help="seed for the dice; each opened campaign draws its own dice seed from it")
    serve.add_argument("--web-dist", default=None, help="built web app folder (default: web/dist in this checkout)")
    serve.add_argument("--referee", choices=["sdk", "none", "scripted"], default="sdk",
                       help="sdk: Claude through the Agent SDK on your plan; none: no Referee; "
                            "scripted: the turns of --script, for tests")
    serve.add_argument("--script", default=None,
                       help='JSON {"dice": [...], "referee": [[{"say": text} | {"call": {tool, input}}, ...], ...]}: '
                            "fixed dice for every campaign, and one list of steps per Referee turn")
    serve.add_argument("--model", default=None, help="set the campaign's Referee model (default: keep it)")
    serve.add_argument("--effort", default=None, help="set the campaign's Referee effort (default: keep it)")
    demo = sub.add_parser("demo", help="create a campaign with a small hand-made map")
    demo.add_argument("campaign")
    args = parser.parse_args(argv)

    try:
        if args.command == "serve":
            flextale_data = default_output_dir(os.environ if env is None else env, home or Path.home())
            plugins = builtin_plugins(flextale_data, OSE_DATA_DIR)
            web_dist = Path(args.web_dist) if args.web_dist else Path(__file__).resolve().parents[3] / "web" / "dist"
            return _serve(args, run or _uvicorn_run, lan_ip, plugins, web_dist)
        return _demo(args)
    except ImportError as exc:
        print(f"solo-harness needs the harness extra ({exc.name} is missing): "
              "uv tool install --editable '.[harness]'", file=sys.stderr)
        return 1
    except HarnessError as exc:
        print(f"solo-harness: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
