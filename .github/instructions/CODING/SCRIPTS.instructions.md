```instructions
---
applyTo: "**/*.py,**/*.ps1,**/*.sh"
---

# Coding Conventions — Scripts

## RULE: Script Locations

| Directory | Purpose | Examples |
|-----------|---------|---------|
| root (`./`) | Main entry-point scripts | `grabber.py` |
| `utils/` | Reusable helper modules | `exchange_rate.py`, `categorizer.py` |

## RULE: Use Script-Relative Paths

When a script references files relative to the project root, use the script's own location as the anchor — **never** `os.getcwd()` or `$PWD`.

### Python

```python
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = SCRIPT_DIR  # script lives at project root
```

### PowerShell

```powershell
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
```

## RULE: Naming Convention

- Use `snake_case` for Python scripts and modules: `grabber.py`, `exchange_rate.py`
- Use `kebab-case` for shell scripts: `setup-env.ps1`

## RULE: Never Create Temporary Scripts in the Workspace Root

- Use the terminal directly for one-off commands.
- If a diagnostic script is needed, prefix it with `diag_`.

## Script Inventory

| Script | Language | Purpose |
|--------|----------|---------|
| `grabber.py` | Python | Main entry point — logs into AliExpress, downloads invoices, builds summary |
```
