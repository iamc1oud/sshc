"""Tests for storage helpers."""

import pathlib

import sshc.config_parser as parser
from sshc import store


def _write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_delete_single_alias_block(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "config"
    _write(cfg, "Host a\n    Port 22\nHost b\n    Port 23\n")
    assert store.delete_host_alias(cfg, "a")
    remaining = [h.alias for h in parser.collect_hosts(cfg)]
    assert remaining == ["b"]


def test_delete_one_of_multi_alias(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "config"
    _write(cfg, "Host a b\n    User u\n")
    assert store.delete_host_alias(cfg, "a")
    assert [h.alias for h in parser.collect_hosts(cfg)] == ["b"]


def test_add_and_update(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "config"
    _write(cfg, "")
    store.add_host_block(cfg, "web", {"hostname": "example.com"})
    assert "web" in [h.alias for h in parser.collect_hosts(cfg)]
    assert store.update_host_option(cfg, "web", "user", "ajay")
    hosts = parser.collect_hosts(cfg)
    assert hosts[0].user == "ajay"


def test_backup_creates_file(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "config"
    _write(cfg, "Host a\n")
    backup = store.backup_config(cfg)
    assert backup.exists()


def test_add_uses_canonical_casing(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "config"
    _write(cfg, "")
    store.add_host_block(
        cfg, "web", {"hostname": "example.com", "identityfile": "~/.ssh/id"}
    )
    text = cfg.read_text(encoding="utf-8")
    assert "HostName example.com" in text
    assert "IdentityFile ~/.ssh/id" in text
