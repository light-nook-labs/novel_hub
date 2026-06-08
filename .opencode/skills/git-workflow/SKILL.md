---
name: git-workflow
description: Standard git branch, commit, merge, and push workflow for this project
---

## What I do
- Create feature branch from main
- Stage and commit changes
- Merge to main with --no-ff
- Push to remote
- Delete feature branch

## Workflow
```bash
git checkout -b <type>/<description>
git add <files>
git commit -m "<type>: <message>"
git checkout main
git merge <type>/<description> --no-ff
git push
git branch -d <type>/<description>
```

## Commit message format
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code refactoring
- `docs:` — documentation
- `test:` — adding tests
- `chore:` — maintenance

## Rules
- Never commit directly to main
- Use `--no-ff` for merge commits
- Delete feature branch after merge
- Push after every merge
