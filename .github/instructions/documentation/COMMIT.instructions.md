```instructions
---
applyTo: "**/*.py,**/*.ps1,**/*.sh,**/*.md,**/*.json,**/*.csv"
---

# Commit — Instructions for Copilot

## When to execute

**Final step of every task — after:**

1. Script runs without errors.
2. Change log updated (`Documentation/CHANGE_LOG.md`).
3. Project doc updated (`Documentation/PROJECT_DOC.md`).

**NEVER push the commit.** Stage and commit only.

## Step 1 — Stage relevant files

Stage only files that belong to the current task.

Files to **always exclude** from staging:
- `invoices/` (downloaded PDFs — user data)
- `.env` (credentials)
- `__pycache__/`, `*.pyc`
- `.venv/`, `venv/`

## Step 2 — Write the commit message

Use **Conventional Commits** format:

```
<type>(<scope>): <short imperative summary>

<body>
```

### Type

| Type | When to use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behaviour change |
| `docs` | Documentation only |
| `chore` | Build, tooling, config changes |

### Scope

`grabber` · `exchange` · `categorizer` · `docs` · `config`

### Summary line rules
- Imperative mood, present tense.
- No trailing period.
- Max 72 characters.
```
