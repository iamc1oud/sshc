"""File storage helpers with backup and atomic writes."""

import datetime
import os
import pathlib
import shutil

import sshc.config_parser as parser

DEFAULT_CONFIG = pathlib.Path.home() / ".ssh" / "config"

_CANONICAL_KEYS = {
    "hostname": "HostName",
    "user": "User",
    "port": "Port",
    "identityfile": "IdentityFile",
}


def _canonical_key(key: str) -> str:
    """Returns canonical ssh config casing for a key.

    Args:
      key: Lowercase option name.

    Returns:
      Canonical casing such as HostName.
    """
    return _CANONICAL_KEYS.get(key.lower(), key)


class SshcError(Exception):
    """Base error for sshc storage failures."""


def resolve_config_path(
    override: str | pathlib.Path | None = None,
) -> pathlib.Path:
    """Resolves the effective ssh config path.

    Args:
      override: Explicit ``--config`` value or None.

    Returns:
      The config path to use.
    """
    if override:
        return pathlib.Path(override).expanduser()
    env_value = os.environ.get("SSH_CONFIG")
    if env_value:
        return pathlib.Path(env_value).expanduser()
    return DEFAULT_CONFIG


def ensure_config_exists(path: pathlib.Path) -> None:
    """Creates parent dir and empty config with secure perms.

    Args:
      path: Config path to ensure.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600, exist_ok=True)
    else:
        os.chmod(path, 0o600)


def backup_config(path: pathlib.Path) -> pathlib.Path:
    """Copies config to a timestamped backup file.

    Args:
      path: Config path to back up.

    Returns:
      Path of the created backup.

    Raises:
      SshcError: If the source file does not exist.
    """
    if not path.exists():
        raise SshcError(f"Config file does not exist: {path}")
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{stamp}")
    shutil.copy2(path, backup)
    return backup


def _write_lines_atomic(path: pathlib.Path, lines: list[str]) -> None:
    """Writes lines atomically preserving 0600 permissions.

    Args:
      path: Destination config path.
      lines: Lines without trailing newlines.
    """
    ensure_config_exists(path)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.writelines(line + "\n" for line in lines)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def delete_host_alias(path: pathlib.Path, alias: str) -> bool:
    """Removes one alias, dropping empty Host blocks.

    Args:
      path: Main config file to edit.
      alias: Host alias to remove.

    Returns:
      True if anything was removed.
    """
    parsed = parser.parse_file(path)
    changed = False
    for block in reversed(parsed.blocks):
        if alias not in block.aliases:
            continue
        changed = True
        remaining = [a for a in block.aliases if a != alias]
        if remaining:
            parsed.lines[block.start_line] = "Host " + " ".join(remaining)
        else:
            del parsed.lines[block.start_line : block.end_line]
            for other in parsed.blocks:
                if other.start_line > block.start_line:
                    shift = block.end_line - block.start_line
                    other.start_line -= shift
                    other.end_line -= shift
    if changed:
        _write_lines_atomic(path, parsed.lines)
    return changed


def add_host_block(
    path: pathlib.Path,
    alias: str,
    options: dict[str, str],
) -> None:
    """Appends a new Host block to the config.

    Args:
      path: Config file to append to.
      alias: New Host alias.
      options: Option mapping such as hostname or user.

    Raises:
      SshcError: If alias already exists in main file.
    """
    parsed = parser.parse_file(path)
    for block in parsed.blocks:
        if alias in block.aliases:
            raise SshcError(f"Host already exists: {alias}")
    lines = list(parsed.lines)
    if lines and lines[-1].strip():
        lines.append("")
    lines.append(f"Host {alias}")
    order = ("hostname", "user", "port", "identityfile")
    for key in order:
        if options.get(key):
            lines.append(f"    {_canonical_key(key)} {options[key]}")
    for key in sorted(options):
        if key not in order and options[key]:
            lines.append(f"    {_canonical_key(key)} {options[key]}")
    _write_lines_atomic(path, lines)


def update_host_option(
    path: pathlib.Path, alias: str, key: str, value: str
) -> bool:
    """Updates or inserts one option inside a Host block.

    Args:
      path: Config file to edit.
      alias: Host alias whose block is edited.
      key: Option name such as ``hostname``.
      value: New option value.

    Returns:
      True if the alias block was found and updated.
    """
    parsed = parser.parse_file(path)
    lowered = key.lower()
    for block in parsed.blocks:
        if alias not in block.aliases:
            continue
        for idx in range(block.start_line + 1, block.end_line):
            split = parser._split_keyword_value(
                parsed.lines[idx].split("#", 1)[0]
            )
            if split is not None and split[0].lower() == lowered:
                parsed.lines[idx] = f"    {split[0]} {value}"
                _write_lines_atomic(path, parsed.lines)
                return True
        parsed.lines.insert(
            block.end_line, f"    {_canonical_key(key)} {value}"
        )
        _write_lines_atomic(path, parsed.lines)
        return True
    return False
