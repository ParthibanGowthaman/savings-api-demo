Stage all changes, commit, push to a feature branch, and open a GitHub PR.

## Instructions

### Step 1: Authenticate with GitHub

1. Read the `.env` file in the project root to get the `GITHUB_TOKEN` value.
2. Export it as `GH_TOKEN` so the GitHub CLI can authenticate:
   ```bash
   export GH_TOKEN="<token from .env>"
   ```
3. Verify authentication works:
   ```bash
   export PATH="/c/Program Files/GitHub CLI:$PATH"
   gh auth status
   ```

### Step 2: Review current changes

1. Run these commands in parallel to understand the repo state:
   ```bash
   git status
   git diff --staged
   git diff
   git log --oneline -5
   ```
2. If there are no changes to commit, inform me and stop.

### Step 3: Stage files

1. Stage all changed and new files using specific file paths (NOT `git add .` or `git add -A`):
   ```bash
   git add file1.py file2.py ...
   ```
2. NEVER stage files that contain secrets (`.env`, credentials, tokens). Warn me if any are present.
3. Run `git status` to verify the staged files look correct.

### Step 4: Create a feature branch

1. If on `main` or `master`, create and switch to a new feature branch BEFORE committing:
   ```bash
   git checkout -b feature/<descriptive-name>
   ```
2. Choose a meaningful branch name based on the changes (e.g., `feature/savings-api-implementation`, `fix/thread-safe-accounts`).
3. If already on a feature branch, use the current branch.

### Step 5: Commit with a descriptive message

1. Write a commit message with a concise subject line (imperative mood, under 72 chars) and a body explaining WHY the change was made.
2. Always use a HEREDOC to preserve formatting:
   ```bash
   git commit -m "$(cat <<'EOF'
   Subject line here

   Body explaining why the change was made, not just what changed.
   Include bullet points for multiple changes if needed.

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```

### Step 6: Push to GitHub

1. Push the branch to origin with tracking:
   ```bash
   git push -u origin <branch-name>
   ```

### Step 7: Open a Pull Request

1. Create the PR using `gh pr create` with `GH_TOKEN` and the GitHub CLI path exported:
   ```bash
   export GH_TOKEN="<token from .env>"
   export PATH="/c/Program Files/GitHub CLI:$PATH"
   gh pr create --base main --title "Short descriptive title" --body "$(cat <<'EOF'
   ## Summary

   - Bullet point describing what changed and why
   - Another bullet point if needed

   ## Test plan

   - [ ] How to verify the changes work
   - [ ] Another verification step

   Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```
2. Return the PR URL to me when done.

## Important
- NEVER force push
- NEVER push to main/master directly
- NEVER skip pre-commit hooks (no --no-verify)
- If a hook fails, fix the issue and retry — do not bypass it
- Ask me before proceeding if anything looks unexpected
- The `GH_TOKEN` env var must be exported in EVERY bash call that uses `gh` (env vars don't persist between tool calls)
- The GitHub CLI path (`/c/Program Files/GitHub CLI`) must also be added to PATH in every `gh` call
