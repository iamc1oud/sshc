"""Tests for config parsing."""

import pathlib

import sshc.config_parser as parser


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_multi_alias_and_options(tmp_path: pathlib.Path) -> None:
    cfg = _write(
        tmp_path / "config",
        "Host web db\n    HostName example.com\n    User ajay\n",
    )
    parsed = parser.parse_file(cfg)
    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].aliases == ["web", "db"]
    assert parsed.blocks[0].options["hostname"] == "example.com"
    hosts = parser.collect_hosts(cfg)
    assert [h.alias for h in hosts] == ["web", "db"]
    assert hosts[0].user == "ajay"


def test_wildcard_detection(tmp_path: pathlib.Path) -> None:
    cfg = _write(
        tmp_path / "config",
        "Host *\n    ForwardAgent yes\nHost app\n    Port 2222\n",
    )
    hosts = parser.collect_hosts(cfg)
    assert hosts[0].is_wildcard
    assert not hosts[1].is_wildcard
    assert hosts[1].port == "2222"


def test_include_expansion(tmp_path: pathlib.Path) -> None:
    extra = _write(tmp_path / "extra", "Host inc\n    User bob\n")
    _write(tmp_path / "config", f"Include {extra.name}\nHost main\n")
    hosts = parser.collect_hosts(tmp_path / "config")
    assert {h.alias for h in hosts} == {"inc", "main"}


def test_first_value_wins(tmp_path: pathlib.Path) -> None:
    cfg = _write(
        tmp_path / "config",
        "Host a\n    Port 22\n    Port 2222\n",
    )
    hosts = parser.collect_hosts(cfg)
    assert hosts[0].port == "22"
