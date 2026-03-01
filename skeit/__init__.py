#!/usr/bin/env python3

import argparse
import sys

from .party import cmd_party

from .cmd_alias import cmd_alias
from .cmd_fff import cmd_fff
from .cmd_mb import cmd_mb
from .cmd_ms import cmd_ms
from .cmd_pff import cmd_pff
from .cmd_wc import cmd_wc


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

    alias_parser = subparsers.add_parser(
        "alias", help="configure git aliases globally via uvx", parents=[common]
    )
    alias_parser.add_argument(
        "--offline", action="store_true", help="use uvx --offline"
    )
    alias_parser.set_defaults(func=cmd_alias)

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

    mb_parser = subparsers.add_parser(
        "mb",
        help="merge origin default branch into branch via worktree",
        parents=[common],
    )
    mb_parser.add_argument("branch", nargs="?", help="branch to merge into")
    mb_parser.add_argument(
        "-c",
        "--continue",
        dest="cont",
        action="store_true",
        help="continue after resolving conflicts",
    )
    mb_parser.add_argument(
        "--abort",
        action="store_true",
        help="abort pending merge and detach worktree",
    )
    mb_parser.set_defaults(func=cmd_mb)

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

    wc_parser = subparsers.add_parser(
        "wc",
        help="show combined git diff --name-status and --numstat",
        parents=[common],
    )
    wc_parser.add_argument(
        "diff_spec", nargs="?", help="diff specification (e.g., origin/main...HEAD)"
    )
    wc_parser.set_defaults(func=cmd_wc)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
