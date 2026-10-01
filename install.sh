#!/usr/bin/env bash
# Installs the sshc CLI from GitHub using uv.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/iamc1oud/sshc/main/install.sh | sh
#   curl -LsSf https://raw.githubusercontent.com/iamc1oud/sshc/main/install.sh | sh -s -- <ref>
#
# <ref> is a branch, tag, or commit (default: main).
set -euo pipefail

REPO="iamc1oud/sshc"
REF="${1:-main}"
PACKAGE="git+https://github.com/${REPO}.git@${REF}"

msg() {
    printf '%s\n' "$*"
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1
}

if ! need_cmd curl; then
    msg "error: curl is required to install sshc." >&2
    exit 1
fi

if ! need_cmd uv; then
    msg "uv not found, installing uv first..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
fi

msg "Installing sshc (${REF})..."
uv tool install --force "${PACKAGE}"

if ! need_cmd sshc; then
    msg ""
    msg "Installed, but sshc is not on PATH."
    msg "Add this to your shell rc and restart your shell:"
    msg '  export PATH="$HOME/.local/bin:$PATH"'
    exit 1
fi

msg ""
msg "Done! Try: sshc list"
sshc --help >/dev/null
