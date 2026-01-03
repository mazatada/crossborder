---
name: cb-focus-balancer
description: Prevent tunnel vision for API OpenAPI endpoint DB schema migration Alembic jobs async retry DLQ webhook inbound integration audit trace_id observability 仕様 変更 設計 API設計 DB設計 ジョブ 非同期 再試行 監査 連携
metadata:
  short-description: Force cross-axis checks across API DB jobs audit ops and surface decision debt.
---

## Selection note

Skill selection may be automatic or explicit depending on the environment.
This document defines mandatory behavior when this skill is selected.
For high-risk changes, invoke this skill by name to guarantee execution.

## Purpose

Prevent tunnel vision by requiring cross-domain evaluation before finalizing a solution.

## Required evaluation axes

You must evaluate the task across all five axes.
API and contract.
Data and migration.
Async jobs and reliability.
Audit and traceability.
Operations and security.

## Output format

Your output must contain exactly three sections.
Cross axis impact map.
Minimum cross axis actions.
Decision debt register.

## Cross axis impact map requirements

For each axis, state what changes, the primary risk, and the system implication.

API and contract must cover request response validation error semantics and backward compatibility.
Data and migration must cover tables columns indexes migration rollback and retention rules.
Async jobs and reliability must cover sync vs async job type state transitions retry backoff DLQ and idempotency.
Audit and traceability must cover audit events trace_id propagation and rationale capture.
Operations and security must cover monitoring metrics alerts auth secrets signing rate limits and PII leakage risk.

## Minimum cross axis actions requirements

Provide at least one concrete and testable action per axis.
Write each action as a complete sentence.
Actions must be verifiable in code config or tests.

## Decision debt register requirements

List deferred decisions with decision default risk and deadline.
If none exist, write Decision Debt None.
