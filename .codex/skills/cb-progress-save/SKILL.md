---
name: cb-progress-save
description: progress save progress log 記録 進捗 保存 セーブ log progress session end wrap up 進捗を記録して 記録して 終了前 まとめ docs progress.log pr_progress.md pr progress
metadata:
  short-description: Save only. Append progress to docs/progress.log and update docs/pr_progress.md and optional serena memory path.
---

## Selection note

Skill selection may be automatic or explicit depending on the environment.
This document defines mandatory behavior when this skill is selected.
If saving is important invoke this skill by name to guarantee execution.

## Purpose

This skill performs progress recording only.
It must not implement features, refactor code, or propose new designs.
It must only write progress artifacts.

## When to use

Use this skill when the user says 進捗を記録して 進捗記録 保存 セーブ or similar.
Use this skill when the user requests end of session wrap up log progress.
If this skill is selected at session end it should record progress once.

## Safety and privacy

Do not store secrets tokens keys credentials or personal data.
If uncertain whether content is sensitive omit it and write redacted.

## Files to update

Primary files.
1 docs/progress.log
2 docs/pr_progress.md

Optional compat file.
If the directory .serena/memories/progress_log exists then also write a session entry there.

If any primary file does not exist create it.

## Timestamp rules

Use local time in ISO 8601 format with timezone offset if available.
Also include the local date in YYYY-MM-DD.

## Content rules

Write concise entries.
Prefer facts over opinions.
Always include next steps.
Always include references to touched specs or files when known.

## Mandatory output format

Your output must contain exactly four sections.
Entry to docs/progress.log.
Update to docs/pr_progress.md.
Optional serena entry decision.
Questions.

Do not add any other sections.

## Entry to docs/progress.log

Append a single new entry at the end of docs/progress.log.
The entry must include.
- timestamp
- context
- summary
- next
- refs

Format.
- YYYY-MM-DDTHH:MM:SS+TZ
  context
  summary
  next
  refs

## Update to docs/pr_progress.md

Add or update a section for the current date.
If a section for YYYY-MM-DD exists append bullets under it.
If not create a new date heading and add bullets.

The section must include.
- what changed
- what remains
- next actions
- refs

## Optional serena entry decision

If .serena/memories/progress_log exists then write a file.
Path format.
.serena/memories/progress_log/YYYY-MM-DD/session_NN.md

NN rules.
NN must be next integer after the highest existing session_NN for the date.

Entry must include.
- timestamp
- context
- summary
- next
- refs

If the directory does not exist state skipped.

## Questions

If any ambiguity blocks correct logging ask short questions.
If no questions write No questions.
