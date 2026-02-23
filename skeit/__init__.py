#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile

from rich.console import Console

from .party import cmd_party

console = Console(highlight=False)
console_stderr = Console(file=sys.stderr, highlight=False)


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
    parts = [f"ahead:[green]{ahead}[/green]"]
    if behind > 0:
        parts.append(f"behind:[red]{behind}[/red]")
    return " ".join(parts)


def fast_forward(branch, upstream):
    if branch == get_current_branch():
        return run(["git", "merge", "--ff-only", upstream])
    else:
        return run(["git", "fetch", ".", upstream + ":" + branch])


def get_repo_root():
    result = run(["git", "rev-parse", "--show-toplevel"])
    return result.stdout.strip() if result.returncode == 0 else None


def get_repo_name():
    repo_root = get_repo_root()
    if repo_root:
        return os.path.basename(repo_root)
    return "repo"


def get_worktree_parent_dir():
    repo_root = get_repo_root()
    if repo_root:
        return os.path.dirname(repo_root)
    return tempfile.gettempdir()


def get_current_branch():
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else None


def branch_exists_local(branch):
    result = run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"])
    return result.returncode == 0


def find_remote_branch(branch):
    result = run(["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"])
    if result.returncode == 0:
        return f"origin/{branch}"
    return None


def has_uncommitted_changes():
    result = run(["git", "status", "--porcelain"])
    if result.returncode != 0:
        return True
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        if status.strip() and not status.startswith("?"):
            return True
    return False


def get_default_branch():
    result = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if result.returncode == 0:
        ref = result.stdout.strip()
        return ref.replace("refs/remotes/origin/", "")
    for branch in ["main", "master"]:
        result = run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"])
        if result.returncode == 0:
            return branch
    return None


def get_worktrees():
    result = run(["git", "worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return []
    worktrees = []
    current = {}
    for line in result.stdout.strip().split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
    if current:
        worktrees.append(current)
    return worktrees


def get_ms_worktree():
    parent_dir = get_worktree_parent_dir()
    repo_name = get_repo_name()
    worktree_path = os.path.join(parent_dir, f".{repo_name}-ms")
    for wt in get_worktrees():
        if wt.get("path") == worktree_path:
            return wt
    return None


def find_pending_ms_worktree():
    wt = get_ms_worktree()
    if wt and is_merge_in_progress(wt["path"]):
        branch = wt.get("branch", "")
        if branch.startswith("refs/heads/"):
            return branch.replace("refs/heads/", ""), wt
    return None, None


def is_merge_in_progress(worktree_path):
    merge_head = os.path.join(worktree_path, ".git", "MERGE_HEAD")
    if os.path.exists(merge_head):
        return True
    return False


def cmd_ms(args):
    quiet = args.quiet
    continue_merge = args.cont
    abort = args.abort
    branch = args.branch

    if abort:
        return cmd_ms_abort(quiet)

    if continue_merge:
        if not branch:
            branch, worktree = find_pending_ms_worktree()
            if not branch:
                print("Error: no pending merge found", file=sys.stderr)
                return 1
        return cmd_ms_continue(branch, quiet)

    if not branch:
        print("Error: branch name required", file=sys.stderr)
        return 1

    pending_branch, pending_wt = find_pending_ms_worktree()
    if pending_wt:
        print(
            f"Error: pending merge for '{pending_branch}' at {pending_wt['path']}",
            file=sys.stderr,
        )
        print("Run 'skeit ms --continue' or 'skeit ms --abort'", file=sys.stderr)
        return 1

    if has_uncommitted_changes():
        print(
            "Error: uncommitted changes detected. Commit or stash first.",
            file=sys.stderr,
        )
        return 1

    default_branch = get_default_branch()
    if not default_branch:
        print(
            "Error: could not determine default branch (main/master)", file=sys.stderr
        )
        return 1

    current = get_current_branch()
    if current == branch:
        print(f"Error: already on branch '{branch}'", file=sys.stderr)
        return 1

    if not branch_exists_local(branch):
        remote_branch = find_remote_branch(branch)
        if not remote_branch:
            print(
                f"Error: branch '{branch}' does not exist locally or on origin",
                file=sys.stderr,
            )
            return 1
        if not quiet:
            print(
                f"Creating local branch '{branch}' tracking '{remote_branch}'...",
                file=sys.stderr,
            )
        result = run(["git", "branch", "--track", branch, remote_branch])
        if result.returncode != 0:
            print(
                f"Error creating local branch: {result.stderr.strip()}", file=sys.stderr
            )
            return 1

    parent_dir = get_worktree_parent_dir()
    repo_name = get_repo_name()
    worktree_path = os.path.join(parent_dir, f".{repo_name}-ms")

    existing_wt = get_ms_worktree()
    if existing_wt:
        if not quiet:
            print(f"Reusing worktree at {worktree_path}...", file=sys.stderr)
        result = subprocess.run(
            ["git", "checkout", branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"Error checking out branch: {result.stderr.strip()}", file=sys.stderr
            )
            return 1
    else:
        os.makedirs(worktree_path, exist_ok=True)
        if not quiet:
            print(f"Creating worktree at {worktree_path}...", file=sys.stderr)
        result = run(["git", "worktree", "add", worktree_path, branch])
        if result.returncode != 0:
            print(f"Error creating worktree: {result.stderr.strip()}", file=sys.stderr)
            os.rmdir(worktree_path)
            return 1

    if not quiet:
        print(f"Merging {default_branch} into {branch}...", file=sys.stderr)

    result = subprocess.run(
        ["git", "merge", default_branch],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        console_stderr.print("[red]Merge conflict detected[/red]")
        print(f"Worktree left at: {worktree_path}", file=sys.stderr)
        print("Resolve conflicts, then run: skeit ms --continue", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    result = run(["git", "checkout", branch])
    if result.returncode != 0:
        print(f"Error switching to branch: {result.stderr.strip()}", file=sys.stderr)
        return 1

    console.print(f"[green]Switched to refreshed branch '{branch}'[/green]")
    return 0


def cmd_ms_continue(branch, quiet):
    worktree = get_ms_worktree()
    if not worktree:
        print("Error: no worktree found", file=sys.stderr)
        return 1

    worktree_path = worktree["path"]

    if not is_merge_in_progress(worktree_path):
        result = run(["git", "-C", worktree_path, "rev-parse", "--verify", "HEAD"])
        if result.returncode != 0:
            print("Error: worktree in unexpected state", file=sys.stderr)
            return 1

    result = subprocess.run(
        ["git", "commit", "--no-edit"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            pass
        else:
            print(f"Error committing merge: {result.stderr.strip()}", file=sys.stderr)
            return 1

    if not quiet:
        print("Detaching worktree...", file=sys.stderr)

    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    result = run(["git", "checkout", branch])
    if result.returncode != 0:
        print(f"Error switching to branch: {result.stderr.strip()}", file=sys.stderr)
        return 1

    console.print(f"[green]Switched to refreshed branch '{branch}'[/green]")
    return 0


def cmd_ms_abort(quiet):
    worktree = get_ms_worktree()
    if not worktree:
        print("Error: no worktree found", file=sys.stderr)
        return 1

    worktree_path = worktree["path"]

    if not quiet:
        print("Aborting merge...", file=sys.stderr)

    subprocess.run(
        ["git", "merge", "--abort"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    if not quiet:
        print("Detaching worktree...", file=sys.stderr)

    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )

    print("Aborted.", file=sys.stderr)
    return 0


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
                console.print(
                    f"{branch} {upstream}: [green]pushed[/green] {format_status(ahead, behind)}"
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
        print(f"\nDone. Pushed {updated} branch(es)", file=sys.stderr)
    return 0


REPO_URL = "git+https://github.com/44/skeit"


def cmd_install(args):
    quiet = args.quiet

    if not quiet:
        print(f"Installing aliases from {REPO_URL}", file=sys.stderr)

    commands = ["fff", "pff", "ms", "party"]
    for cmd in commands:
        alias = f"!uvx --from {REPO_URL} skeit {cmd}"
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

    ms_parser = subparsers.add_parser(
        "ms", help="merge and switch branch via worktree", parents=[common]
    )
    ms_parser.add_argument("branch", nargs="?", help="branch to merge and switch to")
    ms_parser.add_argument(
        "-c",
        "--continue",
        dest="cont",
        action="store_true",
        help="continue after resolving conflicts",
    )
    ms_parser.add_argument(
        "--abort",
        action="store_true",
        help="abort pending merge and detach worktree",
    )
    ms_parser.set_defaults(func=cmd_ms)

    party_parser = subparsers.add_parser(
        "party", help="party mode for merging multiple branches", parents=[common]
    )
    party_sub = party_parser.add_subparsers(dest="party_command", required=True)

    party_start = party_sub.add_parser(
        "start", help="start a new party", parents=[common]
    )
    party_start.add_argument("name", help="name for the party")
    party_start.add_argument(
        "branches", nargs="*", help="additional branches to include"
    )
    party_start.set_defaults(func=cmd_party)

    party_add = party_sub.add_parser(
        "add", help="add a branch to the party", parents=[common]
    )
    party_add.add_argument("branch", help="branch to add")
    party_add.set_defaults(func=cmd_party)

    party_default = party_sub.add_parser(
        "default", help="set the default branch for the party", parents=[common]
    )
    party_default.add_argument("branch", help="branch to set as default")
    party_default.set_defaults(func=cmd_party)

    party_move = party_sub.add_parser(
        "move", help="move a commit from merged view to a branch", parents=[common]
    )
    party_move.add_argument("commit", help="commit hash to move")
    party_move.add_argument("branch", help="target branch")
    party_move.set_defaults(func=cmd_party)

    party_sync = party_sub.add_parser(
        "sync", help="sync the merged view with party branches", parents=[common]
    )
    party_sync.set_defaults(func=cmd_party)

    party_status = party_sub.add_parser(
        "status", help="show party status", parents=[common]
    )
    party_status.set_defaults(func=cmd_party)

    party_finish = party_sub.add_parser(
        "finish", help="finish the party", parents=[common]
    )
    party_finish.set_defaults(func=cmd_party)

    party_continue = party_sub.add_parser(
        "continue", help="continue after resolving conflicts", parents=[common]
    )
    party_continue.set_defaults(func=cmd_party)

    party_abort = party_sub.add_parser(
        "abort", help="abort pending operation", parents=[common]
    )
    party_abort.set_defaults(func=cmd_party)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
