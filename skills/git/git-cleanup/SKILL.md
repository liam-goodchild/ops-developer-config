---
name: git-cleanup
description: Checkout default branch, delete merged local branches, prune remotes, and pull latest
---

Use the bundled Python helper for deterministic branch/tag discovery and Git command execution. Do not prompt for approval; explain the cleanup plan, create it, dry-run it, and apply it.

1. Inspect the repository:

   ```powershell
   python "<skill-dir>\scripts\git-cleanup-helper.py" inspect --target "." --json
   ```

2. Show `default_branch`, `deletable_branches`, and `deletable_tags`, then continue without asking for approval.

3. Create a plan outside the repo:

   ```json
   {
     "delete_branches": ["old-branch"],
     "delete_tags": ["old-tag"],
     "pull": true
   }
   ```

4. Dry-run, then apply:

   ```powershell
   python "<skill-dir>\scripts\git-cleanup-helper.py" apply --target "." --plan "$env:TEMP\git-cleanup.json" --dry-run
   python "<skill-dir>\scripts\git-cleanup-helper.py" apply --target "." --plan "$env:TEMP\git-cleanup.json"
   ```

5. Report deleted branches, deleted tags, fetch/prune, and pull results. The helper uses `git fetch --prune --no-tags` and `git pull --no-tags` so deleted tags are not refetched.
