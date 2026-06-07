---
description: Superpowers plan gate. Writes a small-step plan with files + verification. Must ask for approval before coding.
---

# Superpowers Write Plan (Gate)

## Task
Plan for this task (exactly as provided by the user):
**{{input}}**

If `{{input}}` is empty or missing, ask the user to restate the task in one sentence and STOP.

## Rules
- DO NOT edit code.
- You may read files to understand context, but produce the plan and then stop.
- Plan steps must be small (2–10 minutes each) and include verification commands.

## Output format (use exactly)
## Goal
## Assumptions
## Plan
(Each step must include: Files, Change, Verify)
## Risks & mitigations
## Rollback plan

## Persist (mandatory)
Write the plan output to:
- `artifacts/superpowers/plan.md`

Create the folder if needed.
After writing, confirm it exists by listing `artifacts/superpowers/`.

## Approval
Ask:
**Approve this plan? Reply APPROVED if it looks good.**

If the user replies APPROVED:
- Do NOT implement yet.
- Reply: **"Plan approved. Run `/superpowers-execute-plan` to begin implementation."**
