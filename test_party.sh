#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR=$(mktemp -d)

echo "Test directory: $TEST_DIR"

cleanup() {
    cd "$SCRIPT_DIR"
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

cd "$TEST_DIR"

skeit() {
    PYTHONPATH="$SCRIPT_DIR" python -m skeit "$@"
}

git init
git config user.email "test@test.com"
git config user.name "Test"

echo "file1" > file1.txt
git add file1.txt
git commit -m "Add file1"

echo "file2" > file2.txt
git add file2.txt
git commit -m "Add file2"

git checkout -b branch1
echo "branch1_file" > branch1.txt
git add branch1.txt
git commit -m "Add branch1 file"

git checkout main
git checkout -b branch2
echo "branch2_file" > branch2.txt
git add branch2.txt
git commit -m "Add branch2 file"

git checkout main

echo ""
echo "=== Test 1: party start/finish ==="
skeit party start myparty branch1 branch2
skeit party status
skeit party finish

echo ""
echo "=== Test 2: party start again (reuse worktree) ==="
skeit party start myparty branch1 branch2
skeit party status
skeit party finish

echo ""
echo "SUCCESS!"
