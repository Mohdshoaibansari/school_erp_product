# AGENTS.md

- For OpenSpec propose/apply/verify/archive workflows, use the local `openspec-git-discipline` skill to enforce proposal commits before apply and merge-before-archive discipline.

## Branch Discipline

- **Implementation must happen on `main` branch only.**
- Before running `/opsx-apply`, check current branch with `git branch --show-current`.
- If not on `main`, **stop and remind the user** to switch to main first.
- Syncing specs to main (`/opsx-sync`) should happen **after** implementation confirms specs are correct, not before.
- One spec at a time: sync a single capability spec to main, implement it, verify, then move to the next.
