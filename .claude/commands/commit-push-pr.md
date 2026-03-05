Stage all changes, commit, push to a feature branch, and open a GitHub PR.

## Instructions

1. Run `git status` and `git diff --staged` and `git diff` to review all current changes (staged and unstaged). Also run `git log --oneline -5` to see recent commit message style.

2. If there are no changes to commit, inform me and stop.

3. Stage all changed and new files with `git add` using specific file paths (not `git add .` or `git add -A`). Do NOT stage files that look like secrets (.env, credentials, tokens) — warn me if any are present.

4. Write a commit message that:
   - Has a concise subject line (imperative mood, under 72 chars) summarizing what changed
   - Includes a blank line then a body explaining WHY the change was made (not just what)
   - Ends with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

5. Determine a descriptive feature branch name from the changes (e.g., `feat/add-account-tests`, `fix/thread-safe-accounts`). If already on a feature branch (not `main`/`master`), use the current branch.

6. If on `main` or `master`, create and switch to the new feature branch BEFORE committing.

7. Create the commit.

8. Push the branch to origin with `git push -u origin <branch-name>`.

9. Open a pull request using `gh pr create` targeting the main branch with:
   - A short, descriptive title (under 70 chars)
   - A body containing:
     - `## Summary` — 1-3 bullet points describing the changes
     - `## Test plan` — how to verify the changes work
     - Footer: `Generated with [Claude Code](https://claude.com/claude-code)`
   - Use a HEREDOC for the body to preserve formatting

10. Return the PR URL to me when done.

## Important
- NEVER force push
- NEVER push to main/master directly
- NEVER skip pre-commit hooks (no --no-verify)
- If a hook fails, fix the issue and retry — do not bypass it
- Ask me before proceeding if anything looks unexpected
