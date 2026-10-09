# Git Workflow

One person works on this repo, so the flow is simple. `main` is always the working version. Every change happens on a branch and comes back to `main` when it's reviewed.

## 1. Start from main

```bash
git checkout main
git pull
git checkout -b <type>/<short-name>     # for example: feat/pe-tile, docs/stage-2-plan
```

## 2. Decide, then build

- Write or update the design doc for the stage first (see [PLAN.md](PLAN.md) working agreements).
- Make small commits as you go, using `<type>: <description>` (types: feat, fix, refactor, docs, test, chore, perf, ci).
- Log decisions and surprises in [decision-log.md](decision-log.md) the same day.

## 3. Review before merging

```bash
git diff main...HEAD          # everything this branch changes
make test                     # once the test command exists (Stage 0)
```

Check the diff against the stage's exit criterion. Fix anything that doesn't match, then move on.

## 4. Merge back to main

```bash
git checkout main
git merge --no-ff <branch>    # keeps a record that the branch existed
git push origin main
git branch -d <branch>
git push origin --delete <branch>
```

Use `--no-ff` for feature branches. Use the same steps for docs-only changes.

## Rules

- Don't commit feature work directly on `main`.
- Don't force-push `main`.
- Update the changelog ([CHANGELOG.md](../CHANGELOG.md)) when a stage exits, not on every commit.
- If you want a GitHub PR for a branch, open it against `main` before step 4. You can still merge locally afterwards.
