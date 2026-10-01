"""Legacy entrypoint delegating to sshc CLI."""

from collections.abc import Sequence

from sshc import cli


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the sshc CLI.

    Args:
      argv: Argument list or None for sys.argv.
    """
    cli.main(argv)


if __name__ == "__main__":
    main()
