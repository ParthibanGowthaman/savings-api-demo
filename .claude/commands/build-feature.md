# Build Feature

You are an orchestrator. Build the feature: $ARGUMENTS

---

## Step 1 — Understand the codebase

Run these first:
```bash
cat CLAUDE.md
git status
git log --oneline -5
```

---

## Step 2 — Present a plan

Before writing any code, think through the implementation and present a clear plan:

```
Feature:      $ARGUMENTS

Files to change:
  - <file> — <why>
  - <file> — <why>

Architecture approach:
  <how this fits Routes → Services → Repositories>

Edge cases to handle:
  - <case>
  - <case>

Tests to write:
  - <test scenario>
  - <test scenario>

Security considerations:
  - <anything a bank needs to think about>
```

Wait for approval before proceeding.
Do not write any code until the plan is approved.

---

## Step 3 — Spawn three agents in parallel

Once approved, use the Task tool to run all three simultaneously:

- **implementer** — build the feature following the approved plan
- **test-writer** — write comprehensive tests in parallel
- **security-reviewer** — review for issues and architecture violations

Pass each agent the full feature description: $ARGUMENTS

---

## Step 4 — After all three complete

1. Run the full test suite:
```bash
pytest --tb=short
```

2. If security-reviewer found any HIGH or MEDIUM issues — fix them now

3. Print this summary:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature:   $ARGUMENTS
Files:     <list>
Tests:     <N new> | <total> passing
Security:  <issues fixed or "Clean">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

4. Say: "Ready to ship. Run /commit-push-pr to open the PR."

---

Do not ask questions during implementation. Make decisions, follow CLAUDE.md, report back.
