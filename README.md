# sshc — SSH config manager

List, connect, add, edit, and delete `~/.ssh/config` hosts from one CLI.

## Install

```bash
uv sync
uv run sshc list
# or: pipx install -e .
```

## Usage

```bash
sshc list [--verbose] [--filter <substr>]
sshc connect [<host>] [-- <extra ssh args>...]
sshc delete <host> [--yes]
sshc add <host> --hostname H [--user U --port P --identity F]
sshc edit <host> [--hostname H --user U --port P --identity F]
sshc --config /tmp/test_config list
```

- `connect` with no host opens a numbered picker.
- `delete`/`add`/`edit` create a timestamped `config.bak.YYYYMMDD-HHMMSS`.
- Wildcards (`Host *`) are hidden unless `--verbose`.
- `Include` files are listed read-only; deletes only touch the main file.
- Override path via `--config` or `$SSH_CONFIG`.

## Examples

```bash
sshc list
sshc connect web -- -L 8080:localhost:80
sshc add api --hostname api.example.com --user deploy --port 2222
sshc edit api --user root
sshc delete old-host --yes
```
