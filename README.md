# sshc — SSH config manager

List, connect, add, edit, and delete `~/.ssh/config` hosts from one CLI.

## Install

One-liner (installs `uv` if needed, then `sshc`):

```bash
curl -LsSf https://raw.githubusercontent.com/iamc1oud/sshc/main/install.sh | sh
```

To install a specific branch, tag, or commit:

```bash
curl -LsSf https://raw.githubusercontent.com/iamc1oud/sshc/main/install.sh | sh -s -- <ref>
```

Manual alternatives:

```bash
uv tool install "git+https://github.com/iamc1oud/sshc.git"
# or from a local checkout:
uv sync
uv run sshc list
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
