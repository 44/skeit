import sys

from rich.console import Console

from .utils import (
    can_fast_forward,
    fast_forward,
    format_status,
    get_ahead_behind,
    get_local_branches,
    run,
)

console = Console(highlight=False)


def cmd_fff(args):
    quiet = args.quiet

    branches = get_local_branches()

    if not branches:
        print("No local branches with upstream configured", file=sys.stderr)
        return 0

    remotes = set()
    for _, upstream in branches:
        if "/" in upstream:
            remote = upstream.split("/", 1)[0]
            remotes.add(remote)

    for remote in remotes:
        if not quiet:
            print(f"Fetching {remote}...", file=sys.stderr)
        run(["git", "fetch", remote], capture=False)

    updated = 0
    for branch, upstream in branches:
        ahead, behind = get_ahead_behind(branch, upstream)
        if behind > 0 and can_fast_forward(branch, upstream):
            result = fast_forward(branch, upstream)
            if result.returncode == 0:
                console.print(
                    f"{branch} {upstream}: [green]merged[/green] {format_status(ahead, behind)}"
                )
                updated += 1
            else:
                print(
                    f"{branch} {upstream}: error {result.stderr.strip()}",
                    file=sys.stderr,
                )
        elif ahead > 0 or behind > 0:
            console.print(
                f"{branch} {upstream}: [red]skipped[/red] {format_status(ahead, behind)}"
            )

    if not quiet:
        print(f"\nDone. Updated {updated} branch(es)", file=sys.stderr)
    return 0
