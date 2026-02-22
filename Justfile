lint:
	uvx ruff check .

format:
	uvx ruff format .

check: lint format

release *FLAGS:
	#!/usr/bin/env bash
	set -euo pipefail
	
	dry_run=false
	for arg in {{ FLAGS }}; do
		case "$arg" in
			-n|--dry-run) dry_run=true ;;
		esac
	done
	
	branch=$(git rev-parse --abbrev-ref HEAD)
	if [ "$branch" != "main" ]; then
		echo "Error: not on main branch (current: $branch)" >&2
		exit 1
	fi
	
	if [ -n "$(git status --porcelain)" ]; then
		echo "Error: working tree is not clean" >&2
		exit 1
	fi
	
	version=$(svu next)
	
	if [ "$dry_run" = "true" ]; then
		echo "Dry run: would create tag $version and push to origin"
	else
		echo "Creating tag $version..."
		git tag "$version"
		echo "Pushing tag to origin..."
		git push origin "$version"
	fi
