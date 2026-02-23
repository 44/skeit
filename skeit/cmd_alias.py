import sys

from .utils import run

REPO_URL = "git+https://github.com/44/skeit"


def cmd_alias(args):
    quiet = args.quiet
    offline = args.offline

    if not quiet:
        print(f"Configuring aliases from {REPO_URL}", file=sys.stderr)

    commands = ["fff", "pff", "ms", "party", "wc"]
    for cmd in commands:
        if offline:
            alias = f"!uvx --offline skeit {cmd}"
        else:
            alias = f"!uvx --from {REPO_URL} skeit {cmd}"
        result = run(["git", "config", "--global", f"alias.{cmd}", alias])
        if result.returncode != 0:
            print(
                f"Failed to configure alias.{cmd}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return 1
        if not quiet:
            print(f"Configured: git {cmd}", file=sys.stderr)

    return 0
