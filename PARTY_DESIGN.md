# Party Mode - Detailed Workflow

## Initial State

```
Branches:
- main (checked out): main-1 → main-2 → main-3
- feature1 (based on main): main-1 → main-2 → main-3 → feature1-1 → feature1-2 → feature1-3
- feature2 (separate from main): feature2-1 → feature2-2 → feature2-3

Main worktree: /repo (on main)
Party worktree: does not exist
```

---

## `party start myparty feature1 feature2`

### Step 1: Validation
- Check no active party exists
- Check working tree is clean
- Verify branches exist locally
- Check `party/myparty` doesn't already exist

### Step 2: Save config
```
git config --local party.active myparty
git config --local party.myparty.default main
git config --local party.myparty.branches main,feature1,feature2
```

### Step 3: Create worktree
```
git worktree add --detach /repo/../.repo-party HEAD
```

**Main worktree:** `/repo` (still on `main`)
**Party worktree:** `/repo/../.repo-party` (detached HEAD at `main-3`)

### Step 4: Build merged view in worktree
```bash
# In party worktree:
git checkout --detach main         # HEAD at main-3
git merge feature1 --no-edit       # HEAD at merge(f1), includes feature1-1,2,3
git merge feature2 --no-edit       # HEAD at merge(f2), includes feature2-1,2,3
git rev-parse HEAD                 # Get commit hash: ABC123
```

**Party worktree state:**
```
ABC123 (detached HEAD)
├── main-1 → main-2 → main-3
├── feature1-1 → feature1-2 → feature1-3
└── feature2-1 → feature2-2 → feature2-3
```

### Step 5: Create party branch in main repo
```bash
# In main worktree:
git branch party/myparty ABC123
git checkout party/myparty
```

**Final state:**

```
Main worktree (/repo):
- Checked out: party/myparty (at ABC123)
- Branches: main, feature1, feature2, party/myparty

Party worktree (/repo/../.repo-party):
- Detached HEAD at ABC123
- Same content as party/myparty
```

---

## `party status`

### Step 1: Get active party
```
git config --local party.active  # Returns: myparty
```

### Step 2: Get party config
```
git config --local party.myparty.default   # Returns: main
git config --local party.myparty.branches  # Returns: main,feature1,feature2
```

### Step 3: Show branches and commits
```
git log --no-merges --format=%H %s main ^main   # 3 commits (main-1,2,3)
git log --no-merges --format=%H %s feature1 ^feature1   # 3 commits
git log --no-merges --format=%H %s feature2 ^feature2   # 3 commits
```

### Step 4: Show unassigned commits on party branch
```
git log --no-merges --format=%H %s party/myparty ^main ^feature1 ^feature2
```
Returns: merge commits only (excluded by --no-merges), so empty.

**Output:**
```
Active party: myparty
Default branch: main

Branch         Commits
main (default) 3
feature1       3
feature2       3
```

---

## User makes commits on `party/myparty`

User works normally in main worktree:
```bash
echo "work1" > work1.txt && git add . && git commit -m "work-1"
echo "work2" > work2.txt && git add . && git commit -m "work-2"
```

**State:**
```
party/myparty: ABC123 → work-1 → work-2
```

---

## `party sync`

### Step 1: Validation
- Check active party exists
- Check working tree is clean

### Step 2: Detect unique commits
```bash
git log --no-merges --format=%H %s party/myparty ^main ^feature1 ^feature2
```
Returns: `work-1`, `work-2` (commits only on party/myparty)

### Step 3: Move commits to default branch
```bash
# In party worktree:
git checkout main
git cherry-pick work-1
git cherry-pick work-2
```

**Party worktree state:**
```
main: main-1 → main-2 → main-3 → work-1 → work-2
```

### Step 4: Rebuild merged view
```bash
# In party worktree:
git checkout --detach main
git merge feature1 --no-edit
git merge feature2 --no-edit
git rev-parse HEAD   # Get new hash: DEF456
```

### Step 5: Update party branch
```bash
# In main worktree:
git branch -f party/myparty DEF456
git checkout party/myparty
```

**Final state:**
```
Main worktree: party/myparty (at DEF456)
Party worktree: detached HEAD at DEF456

main: main-1 → main-2 → main-3 → work-1 → work-2
feature1: ... → feature1-3
feature2: ... → feature2-3
party/myparty: DEF456 (merge of main + feature1 + feature2)
```

---

## `party finish`

### Step 1: Sync
Runs `party sync` internally.

### Step 2: Checkout default branch
```bash
git checkout main
```

### Step 3: Delete party branch
```bash
git branch -D party/myparty
```

### Step 4: Remove worktree
```bash
git worktree remove /repo/../.repo-party --force
```

### Step 5: Clean config
```bash
git config --local --unset party.active
git config --local --unset party.myparty.default
git config --local --unset party.myparty.branches
```

**Final state:**
```
Main worktree: main (contains all work commits)
Party worktree: deleted

main: main-1 → main-2 → main-3 → work-1 → work-2
feature1: unchanged
feature2: unchanged
```

---

## `party add feature3`

### Step 1: Validation
- Check active party exists
- Verify branch exists locally

### Step 2: Update config
```bash
git config --local party.myparty.branches main,feature1,feature2,feature3
```

### Step 3: Sync (rebuild with new branch)
Rebuilds merged view including feature3.

---

## `party move <commit> feature1`

Move a commit from party/myparty to feature1.

### Step 1: Validation
- Active party exists
- Working tree clean
- Target branch is in party

### Step 2: Cherry-pick to target
```bash
# In party worktree:
git checkout feature1
git cherry-pick <commit>
```

### Step 3: Sync (rebuild without that commit on party branch)
The commit is now on feature1, so rebuild will include it via feature1.

---

## Key Invariants

1. **Party branch only exists in main worktree** - never checked out in party worktree
2. **Party worktree is always detached HEAD** - used only for building merged views
3. **Work happens in main worktree** on `party/<name>` branch
4. **Unique commits** = commits on party branch not reachable from any party member branch
5. **Sync moves unique commits to default branch**, then rebuilds merged view

---

## Git Command Summary

| Command | Location | Git Commands |
|---------|----------|--------------|
| `party start` | main | `config`, `worktree add`, `branch`, `checkout` |
| `party start` | worktree | `checkout --detach`, `merge` |
| `party sync` | worktree | `checkout`, `cherry-pick`, `checkout --detach`, `merge` |
| `party sync` | main | `branch -f`, `checkout` |
| `party finish` | main | `checkout`, `branch -D`, `worktree remove`, `config --unset` |
| `party status` | main | `config`, `log` |
