---
description: Systematic debugging workflow: reproduce, minimize, hypotheses, instrument, fix, prevent, verify.
---

# Superpowers Debug

Use the required reporting format:
- Symptom
- Repro steps
- Root cause
- Fix
- Regression protection
- Verification

## Persist (mandatory)
After generating the debug content above, you MUST write it to disk:

1) Copy the full debug markdown output.
2) Save to: `artifacts/superpowers/debug.md`

After writing, confirm it exists by listing `artifacts/superpowers/`.

Do not implement changes in this workflow. Stop after persistence.
