"""Parse OpenSSH client config files preserving formatting.

Supports ``Host`` blocks, multi-alias lines, wildcard detection,
and read-only ``Include`` expansion. Comments and blank lines are
kept verbatim so rewrites do not reformat unrelated entries.
"""

import dataclasses
import glob
import os
import pathlib


@dataclasses.dataclass
class HostBlock:
    """One Host block with its raw source lines."""

    aliases: list[str]
    options: dict[str, str]
    source_file: pathlib.Path
    start_line: int
    end_line: int


@dataclasses.dataclass
class ParsedConfig:
    """Raw lines plus Host blocks found in one file."""

    lines: list[str]
    blocks: list[HostBlock]
    path: pathlib.Path


@dataclasses.dataclass
class HostEntry:
    """Per-alias view used for listing and connecting."""

    alias: str
    hostname: str | None
    user: str | None
    port: str | None
    identityfile: str | None
    source_file: pathlib.Path
    is_wildcard: bool


def is_wildcard_alias(alias: str) -> bool:
    """Returns True if an alias contains ssh wildcards.

    Args:
      alias: A Host alias such as ``web`` or ``*.example``.

    Returns:
      True when alias contains ``*``, ``?``, or ``!``.
    """
    return any(c in alias for c in ("*", "?", "!"))


def _split_keyword_value(line: str) -> tuple[str, str] | None:
    """Splits a config line into keyword and value.

    Args:
      line: A single stripped config line without comments.

    Returns:
      A keyword/value pair, or None for blank lines.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" in stripped:
        key, _, value = stripped.partition("=")
        return key.strip(), value.strip().strip("\"'")
    parts = stripped.split(None, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1].strip().strip("\"' ")


def parse_file(path: pathlib.Path) -> ParsedConfig:
    """Parses a single ssh config file without following Include.

    Args:
      path: Path to the ssh config file.

    Returns:
      Parsed lines and Host blocks for that file only.
    """
    lines: list[str] = []
    if path.exists():
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    blocks: list[HostBlock] = []
    current_aliases: list[str] | None = None
    current_options: dict[str, str] = {}
    block_start = 0
    for index, raw in enumerate(lines):
        parsed = _split_keyword_value(raw.split("#", 1)[0])
        if parsed is None:
            continue
        key, value = parsed
        if key.lower() == "host":
            if current_aliases is not None:
                blocks.append(
                    HostBlock(
                        aliases=current_aliases,
                        options=current_options,
                        source_file=path,
                        start_line=block_start,
                        end_line=index,
                    )
                )
            current_aliases = value.split() if value else []
            current_options = {}
            block_start = index
        elif current_aliases is not None:
            lowered = key.lower()
            if lowered not in current_options:
                current_options[lowered] = value
    if current_aliases is not None:
        blocks.append(
            HostBlock(
                aliases=current_aliases,
                options=current_options,
                source_file=path,
                start_line=block_start,
                end_line=len(lines),
            )
        )
    return ParsedConfig(lines=lines, blocks=blocks, path=path)


def _expand_include(pattern: str, base: pathlib.Path) -> list[pathlib.Path]:
    """Expands one Include pattern to existing file paths.

    Args:
      pattern: Raw Include value which may contain globs and ``~``.
      base: Config file that declared the Include.

    Returns:
      Sorted list of existing file paths.
    """
    expanded = os.path.expanduser(pattern)
    candidate = pathlib.Path(expanded)
    if not candidate.is_absolute():
        candidate = base.parent / candidate
    matches = glob.glob(str(candidate), recursive=True)
    found = [pathlib.Path(m) for m in matches if os.path.isfile(m)]
    return sorted(found)


def collect_hosts(
    config_path: pathlib.Path,
    _visited: set[pathlib.Path] | None = None,
) -> list[HostEntry]:
    """Collects hosts from a config plus its Includes.

    Args:
      config_path: Main ssh config path.
      _visited: Internal guard against Include loops.

    Returns:
      One entry per alias in file order.
    """
    visited = _visited if _visited is not None else set()
    resolved = config_path.expanduser()
    if resolved in visited:
        return []
    visited.add(resolved)
    parsed = parse_file(resolved)
    entries: list[HostEntry] = []
    for block in parsed.blocks:
        for alias in block.aliases:
            entries.append(
                HostEntry(
                    alias=alias,
                    hostname=block.options.get("hostname"),
                    user=block.options.get("user"),
                    port=block.options.get("port"),
                    identityfile=block.options.get("identityfile"),
                    source_file=block.source_file,
                    is_wildcard=is_wildcard_alias(alias),
                )
            )
    for raw in parsed.lines:
        split = _split_keyword_value(raw.split("#", 1)[0])
        if split is None:
            continue
        key, value = split
        if key.lower() != "include" or not value:
            continue
        for pattern in value.split():
            for match in _expand_include(pattern, resolved):
                entries.extend(collect_hosts(match, visited))
    return entries
