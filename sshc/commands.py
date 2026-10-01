"""Command implementations for list, connect, delete, add, edit."""

import os
import pathlib
import sys

import sshc.config_parser as parser
from sshc import store


def _connectable(
    entries: list[parser.HostEntry], verbose: bool
) -> list[parser.HostEntry]:
    """Filters entries for display and connection.

    Args:
      entries: All collected hosts.
      verbose: Include wildcard entries when True.

    Returns:
      Filtered host entries.
    """
    if verbose:
        return entries
    found: list[parser.HostEntry] = []
    for entry in entries:
        if not entry.is_wildcard:
            found.append(entry)
    return found


def cmd_list(
    config: pathlib.Path,
    verbose: bool = False,
    host_filter: str | None = None,
) -> int:
    """Lists hosts in a table.

    Args:
      config: Ssh config path.
      verbose: Show wildcards and source file.
      host_filter: Optional substring filter.

    Returns:
      Process exit code.
    """
    entries = parser.collect_hosts(config)
    entries = _connectable(entries, verbose)
    if host_filter:
        needle = host_filter.lower()
        entries = [e for e in entries if needle in e.alias.lower()]
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for entry in entries:
            print(f"{entry.alias:<20} {entry.hostname or ''}")
        return 0
    table = Table(title=f"SSH hosts ({len(entries)})")
    table.add_column("#", justify="right")
    table.add_column("Host")
    table.add_column("HostName")
    table.add_column("User")
    table.add_column("Port")
    if verbose:
        table.add_column("Source")
    for index, entry in enumerate(entries, start=1):
        row = [
            str(index),
            entry.alias,
            entry.hostname or "",
            entry.user or "",
            entry.port or "",
        ]
        if verbose:
            row.append(str(entry.source_file))
        table.add_row(*row)
    Console().print(table)
    return 0


def cmd_connect(
    config: pathlib.Path,
    alias: str | None,
    extra_args: list[str] | None = None,
) -> int:
    """Connects via ssh, prompting when alias is missing.

    Args:
      config: Ssh config path.
      alias: Host alias or None for interactive picker.
      extra_args: Extra args passed through to ssh.

    Returns:
      Process exit code (exec replaces process on success).
    """
    entries = _connectable(parser.collect_hosts(config), False)
    names = {entry.alias: entry for entry in entries}
    target = alias
    if target is None:
        from sshc import picker

        picked = picker.pick_host(entries)
        if picked is None:
            return 1
        target = picked.alias
    if target not in names:
        print(f"Unknown host: {target}", file=sys.stderr)
        return 1
    command = ["ssh", target]
    command.extend(extra_args or [])
    print(f"Connecting: {' '.join(command)}")
    os.execvp("ssh", command)
    return 0


def _validate_alias(alias: str) -> None:
    """Validates a new Host alias.

    Args:
      alias: Proposed alias.

    Raises:
      store.SshcError: If alias is empty or contains spaces.
    """
    if not alias or not alias.strip():
        raise store.SshcError("Host alias must not be empty.")
    if any(c.isspace() for c in alias):
        raise store.SshcError("Host alias must not contain spaces.")
    if parser.is_wildcard_alias(alias):
        raise store.SshcError(f"Refusing wildcard for new host: {alias}")


def cmd_delete(
    config: pathlib.Path, alias: str, assume_yes: bool = False
) -> int:
    """Deletes a host after backup and confirmation.

    Args:
      config: Ssh config path.
      alias: Host alias to delete.
      assume_yes: Skip confirmation prompt.

    Returns:
      Process exit code.
    """
    main_blocks = parser.parse_file(config).blocks
    found_main = any(alias in b.aliases for b in main_blocks)
    if not found_main:
        all_names = {e.alias for e in parser.collect_hosts(config)}
        if alias in all_names:
            print(
                "Host lives in an Included file; not edited.", file=sys.stderr
            )
            return 1
        print(f"Unknown host: {alias}", file=sys.stderr)
        return 1
    if not assume_yes:
        try:
            raw = input(f"Delete Host {alias}? [y/N]: ")
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return 1
        if raw.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1
    store.ensure_config_exists(config)
    backup = store.backup_config(config)
    print(f"Backup: {backup}")
    removed = store.delete_host_alias(config, alias)
    if removed:
        print(f"Deleted Host {alias}")
    else:
        print("No change.")
    return 0 if removed else 1


def cmd_add(
    config: pathlib.Path,
    alias: str,
    hostname: str | None,
    user: str | None = None,
    port: str | None = None,
    identityfile: str | None = None,
) -> int:
    """Adds a new Host block.

    Args:
      config: Ssh config path.
      alias: New Host alias.
      hostname: HostName value.
      user: Optional User value.
      port: Optional Port value.
      identityfile: Optional IdentityFile value.

    Returns:
      Process exit code.
    """
    try:
        _validate_alias(alias)
    except store.SshcError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not hostname:
        print("--hostname is required.", file=sys.stderr)
        return 1
    store.ensure_config_exists(config)
    backup = store.backup_config(config)
    print(f"Backup: {backup}")
    options: dict[str, str] = {"hostname": hostname}
    if user:
        options["user"] = user
    if port:
        options["port"] = port
    if identityfile:
        options["identityfile"] = identityfile
    try:
        store.add_host_block(config, alias, options)
    except store.SshcError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Added Host {alias}")
    return 0


def cmd_edit(
    config: pathlib.Path,
    alias: str,
    hostname: str | None = None,
    user: str | None = None,
    port: str | None = None,
    identityfile: str | None = None,
) -> int:
    """Edits options of an existing Host block.

    Args:
      config: Ssh config path.
      alias: Host alias to edit.
      hostname: New HostName or None to leave unchanged.
      user: New User or None to leave unchanged.
      port: New Port or None to leave unchanged.
      identityfile: New IdentityFile or None to leave unchanged.

    Returns:
      Process exit code.
    """
    updates = {
        "hostname": hostname,
        "user": user,
        "port": port,
        "identityfile": identityfile,
    }
    updates = {k: v for k, v in updates.items() if v is not None}
    if not updates:
        print("Nothing to update; pass --hostname/--user.", file=sys.stderr)
        return 1
    store.ensure_config_exists(config)
    backup = store.backup_config(config)
    print(f"Backup: {backup}")
    changed = False
    for key, value in updates.items():
        updated = store.update_host_option(config, alias, key, value or "")
        changed = changed or updated
    if not changed:
        print(f"Unknown host: {alias}", file=sys.stderr)
        return 1
    print(f"Updated Host {alias}")
    return 0
