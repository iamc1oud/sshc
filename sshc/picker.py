"""Interactive numbered picker for ssh hosts."""

import sys

import sshc.config_parser as parser


def pick_host(
    hosts: list[parser.HostEntry],
) -> parser.HostEntry | None:
    """Prompts user to pick one host by number.

    Args:
      hosts: Non-wildcard hosts in display order.

    Returns:
      The chosen entry, or None on abort or empty input.
    """
    if not hosts:
        print("No hosts found.", file=sys.stderr)
        return None
    for index, entry in enumerate(hosts, start=1):
        detail = entry.hostname or ""
        print(f"{index:3d}  {entry.alias:<20} {detail}")
    try:
        raw = input(f"Select [1-{len(hosts)}] (Enter to abort): ")
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return None
    raw = raw.strip()
    if not raw:
        return None
    if not raw.isdigit():
        print(f"Invalid selection: {raw}", file=sys.stderr)
        return None
    number = int(raw)
    if number < 1 or number > len(hosts):
        print(f"Out of range: {number}", file=sys.stderr)
        return None
    return hosts[number - 1]
