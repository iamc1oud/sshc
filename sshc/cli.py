"""Argparse entrypoint for the sshc CLI."""

import argparse
import sys
from collections.abc import Sequence

from sshc import commands, store


def build_parser() -> argparse.ArgumentParser:
    """Builds the top-level argument parser.

    Returns:
      Configured ArgumentParser.
    """
    top = argparse.ArgumentParser(
        prog="sshc", description="Manage ssh config hosts."
    )
    top.add_argument(
        "--config",
        default=None,
        help="Ssh config path (default ~/.ssh/config).",
    )
    subs = top.add_subparsers(dest="command")

    listed = subs.add_parser("list", help="List hosts.")
    listed.add_argument("--verbose", action="store_true")
    listed.add_argument("--filter", default=None)

    connected = subs.add_parser("connect", help="Connect to a host.")
    connected.add_argument("host", nargs="?")
    connected.add_argument(
        "extra", nargs=argparse.REMAINDER, help="Extra ssh args after --."
    )

    deleted = subs.add_parser("delete", help="Delete a host.")
    deleted.add_argument("host")
    deleted.add_argument("--yes", action="store_true")

    added = subs.add_parser("add", help="Add a host.")
    added.add_argument("host")
    added.add_argument("--hostname", default=None)
    added.add_argument("--user", default=None)
    added.add_argument("--port", default=None)
    added.add_argument("--identity", default=None)

    edited = subs.add_parser("edit", help="Edit a host.")
    edited.add_argument("host")
    edited.add_argument("--hostname", default=None)
    edited.add_argument("--user", default=None)
    edited.add_argument("--port", default=None)
    edited.add_argument("--identity", default=None)
    return top


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the sshc CLI.

    Args:
      argv: Argument list or None for sys.argv.
    """
    args = build_parser().parse_args(argv)
    config = store.resolve_config_path(args.config)
    code = 0
    if args.command == "list" or args.command is None:
        filt = getattr(args, "filter", None)
        verbose = getattr(args, "verbose", False)
        if args.command is None and sys.stdin.isatty():
            code = commands.cmd_list(config, verbose, filt)
            print("\nTip: sshc connect <host> to connect.")
        else:
            code = commands.cmd_list(config, verbose, filt)
    elif args.command == "connect":
        extra = [a for a in (args.extra or []) if a != "--"]
        code = commands.cmd_connect(config, args.host, extra)
    elif args.command == "delete":
        code = commands.cmd_delete(config, args.host, args.yes)
    elif args.command == "add":
        code = commands.cmd_add(
            config,
            args.host,
            args.hostname,
            args.user,
            args.port,
            args.identity,
        )
    elif args.command == "edit":
        code = commands.cmd_edit(
            config,
            args.host,
            args.hostname,
            args.user,
            args.port,
            args.identity,
        )
    else:
        code = 2
    if code != 0:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
