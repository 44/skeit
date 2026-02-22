# Skeit

## Commands

### fetch-fast-forward (fff)

Fetches upstream for all local branches, goes through them and fast-forwards those that can be fast-forwarded.

### push-fast-forward (pff)

Pushes all local branches to their upstream, but only if they can be fast-forwarded.

### merge-switch (ms)

Merges specified branch with the default branch of upstream, then switches to it. Merge happens
in separate worktree, if it fails user can fix it there and run `ms --continue` to continue the process.

