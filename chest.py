#!/usr/bin/env python3
"""chest: git helper tools"""

import argparse
import subprocess
import sys


def run(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result


def get_local_branches():
    result = run(["git", "branch", "--format=%(refname:short) %(upstream:short)"])
    if result.returncode != 0:
        return []

    branches = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        branch = parts[0]
        upstream = parts[1].strip() if len(parts) > 1 else None
        if upstream:
            branches.append((branch, upstream))
    return branches


def can_fast_forward(branch, upstream):
    result = run(["git", "merge-base", "--is-ancestor", branch, upstream])
    return result.returncode == 0


def get_ahead_behind(branch, upstream):
    result = run(
        ["git", "rev-list", "--left-right", "--count", f"{branch}...{upstream}"]
    )
    if result.returncode == 0:
        ahead, behind = result.stdout.strip().split()
        return int(ahead), int(behind)
    return 0, 0


def format_status(ahead, behind):
    parts = [f"ahead:{ahead}"]
    if behind > 0:
        parts.append(f"behind:{behind}")
    return " ".join(parts)


def fast_forward(branch, upstream):
    if branch == get_current_branch():
        return run(["git", "merge", "--ff-only", upstream])
    else:
        return run(["git", "fetch", ".", upstream + ":" + branch])


def get_current_branch():
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else None


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
                print(f"{branch} {upstream}: merged {format_status(ahead, behind)}")
                updated += 1
            else:
                print(
                    f"{branch} {upstream}: error {result.stderr.strip()}",
                    file=sys.stderr,
                )
        elif ahead > 0 or behind > 0:
            print(f"{branch} {upstream}: skipped {format_status(ahead, behind)}")

    if not quiet:
        print(f"\nDone. Updated {updated} branch(es)", file=sys.stderr)
    return 0


def cmd_pff(args):
    quiet = args.quiet

    branches = get_local_branches()

    if not branches:
        print("No local branches with upstream configured", file=sys.stderr)
        return 0

    updated = 0
    for branch, upstream in branches:
        ahead, behind = get_ahead_behind(branch, upstream)
        if ahead > 0 and behind == 0:
            remote = upstream.split("/", 1)[0] if "/" in upstream else None
            if not remote:
                continue
            result = run(["git", "push", remote, branch])
            if result.returncode == 0:
                print(f"{branch} {upstream}: pushed {format_status(ahead, behind)}")
                updated += 1
            else:
                print(
                    f"{branch} {upstream}: error {result.stderr.strip()}",
                    file=sys.stderr,
                )
        elif ahead > 0 or behind > 0:
            print(f"{branch} {upstream}: skipped {format_status(ahead, behind)}")

    if not quiet:
        print(f"\nDone. Pushed {updated} branch(es)", file=sys.stderr)
    return 0


def get_origin_url():
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if url.startswith("git@"):
        url = url.replace(":", "/", 1).replace("git@", "https://")
    if url.endswith(".git"):
        url = url[:-4]
    return f"git+{url}"


def cmd_install(args):
    quiet = args.quiet

    url = get_origin_url()
    if not url:
        print("No origin remote found", file=sys.stderr)
        return 1

    if not quiet:
        print(f"Installing aliases from {url}", file=sys.stderr)

    commands = ["fff", "pff"]
    for cmd in commands:
        alias = f"!uvx --from {url} chest {cmd}"
        result = run(["git", "config", "--global", f"alias.{cmd}", alias])
        if result.returncode != 0:
            print(
                f"Failed to install alias.{cmd}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return 1
        if not quiet:
            print(f"Installed: git {cmd}", file=sys.stderr)

    return 0


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress messages"
    )

    parser = argparse.ArgumentParser(description="git helper tools", parents=[common])
    subparsers = parser.add_subparsers(dest="command", required=True)

    fff_parser = subparsers.add_parser(
        "fff", help="fetch and fast-forward local branches", parents=[common]
    )
    fff_parser.set_defaults(func=cmd_fff)

    pff_parser = subparsers.add_parser(
        "pff", help="push local branches ahead of upstream", parents=[common]
    )
    pff_parser.set_defaults(func=cmd_pff)

    install_parser = subparsers.add_parser(
        "install", help="install git aliases globally via uvx", parents=[common]
    )
    install_parser.set_defaults(func=cmd_install)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
