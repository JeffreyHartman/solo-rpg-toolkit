"""solo-harness: create a demo campaign, or serve a campaign to the browser."""
import argparse
import socket
import sys
from collections.abc import Callable
from pathlib import Path

from ..rng import RandomDice
from .campaign import CampaignPaths, create_campaign
from .demo import DEMO_MAP, DEMO_PARTY, DEMO_START
from .engine import open_campaign
from .errors import HarnessError
from .plugins import BUILTIN_PLUGINS

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


def _serve(args, run: Callable, find_ip: Callable[[], str]) -> int:
    from .server import create_app

    engine = open_campaign(Path(args.campaign), RandomDice(seed=args.seed), BUILTIN_PLUGINS)
    referee = None
    if args.referee == "sdk":
        from .referee.sdk import AgentSdkReferee

        referee = AgentSdkReferee(engine, CampaignPaths(Path(args.campaign)), model=args.model, effort=args.effort)
    web_dist = Path(args.web_dist) if args.web_dist else Path(__file__).resolve().parents[3] / "web" / "dist"
    print(f"Harness for {args.campaign}: http://{find_ip()}:{args.port}/", flush=True)
    run(create_app(engine, web_dist=web_dist, referee=referee), host=BIND_HOST, port=args.port)
    return 0


def _demo(args) -> int:
    root = create_campaign(
        Path(args.campaign), plugins=["ose"], map_data=DEMO_MAP, start=DEMO_START, party=DEMO_PARTY
    )
    print(f"Demo campaign created at {root}. Run: solo-harness serve {root}")
    return 0


def main(
    argv: list[str] | None = None,
    run: Callable | None = None,
    lan_ip: Callable[[], str] = lan_ip,
) -> int:
    parser = argparse.ArgumentParser(prog="solo-harness")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="serve a campaign on the LAN")
    serve.add_argument("campaign")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--seed", type=int, default=None)
    serve.add_argument("--web-dist", default=None, help="built web app folder (default: web/dist in this checkout)")
    serve.add_argument("--referee", choices=["sdk", "none"], default="sdk",
                       help="sdk: Claude through the Agent SDK on your plan; none: no Referee")
    serve.add_argument("--model", default="sonnet")
    serve.add_argument("--effort", default="low")
    demo = sub.add_parser("demo", help="create a campaign with a small hand-made map")
    demo.add_argument("campaign")
    args = parser.parse_args(argv)

    try:
        if args.command == "serve":
            return _serve(args, run or _uvicorn_run, lan_ip)
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
