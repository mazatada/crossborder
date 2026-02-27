# Progress logging policy

When the session ends or the user says "進捗を記録して":

1) Write a progress entry to `.serena/memories/progress_log/YYYY-MM-DD/session_<NN>.md`.
   - NN is the next number after the latest existing `session_<NN>.md` for that date.
   - Use the ISO 8601 local timestamp and include context/summary/next/refs.

2) Update `docs/pr_progress_20251220.md` with a new date-stamped summary section.

Notes:
- Keep entries concise and consistent with existing progress formats.
- Do not store secrets or PII.
