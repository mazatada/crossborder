---
name: cb-memory-guard
description: Enforce invariants before changing API OpenAPI endpoint DB schema migration Alembic jobs async retry DLQ webhook inbound integration audit trace_id observability security compatibility PII retention 仕様 変更 設計 API設計 DB設計 ジョブ 非同期 再試行 監査 trace_id 可観測性 セキュリティ 後方互換 PII 最小保持
metadata:
  short-description: Enforce non negotiable invariants for compliance core system PII禁止 監査必須 非同期 後方互換は追加のみ.
---

## Selection note

Skill selection may be automatic or explicit depending on the environment.
This document defines mandatory behavior when this skill is selected.
For high risk changes invoke this skill by name to guarantee execution.

## Purpose

Replace long term project memory by enforcing non negotiable invariants and boundaries.
Prevent drift in scope data retention auditability async execution and backward compatibility.

## When to use

Use this skill before designing or changing API specs database schema async jobs integrations security audit or observability.
Use this skill when the user asks should we can we is it ok or when proposing any change refactor or new feature.

## Non negotiable invariants

The system must be explainable.
The system must be auditable.
The system must minimize data retention and must not store PII.
The system must remain loosely coupled and must not implement sales marketing payments inventory or analytics.
Changes must be additive only and must not remove fields or change meanings.

## System boundaries

This system owns ingredient translation HS classification customs documents PN minimal integration async jobs audit and webhooks.
This system does not own customers revenue inventory payments or marketing analytics.

## Integration policy

Inbound receives minimal external events only and must not persist order details or customer attributes.
Outbound uses signed webhooks and must support retries DLQ and manual replay.

## Async execution model

Long running or external dependent operations must be executed asynchronously.
Async execution must use a jobs table with explicit state transitions retry backoff and DLQ.

## Audit and traceability

A trace_id must exist for every request and job.
trace_id must propagate across API to job to webhook.
Audit events must be emitted for critical decisions state transitions and manual overrides.

## Mandatory output format

Your output must contain exactly three sections.
Applied invariants.
Violation risk assessment.
Minimum alignment checklist.

Do not add any other sections.

## Applied invariants requirements

List which invariants and boundaries apply to the current task.

## Violation risk assessment requirements

Explicitly state whether the task risks violating scope retention async audit trace or compatibility.
If no risk exists state No invariant violations detected.

## Minimum alignment checklist requirements

Answer all items below.

Scope and retention.
Confirm no PII or customer data storage and no marketing or sales responsibility.

Audit and trace.
State where trace_id is created where it is propagated and which audit events are emitted.

Async and reliability.
State whether behavior is sync or async and if async define retry backoff and DLQ.

Compatibility.
Confirm the change is additive only and existing clients work without modification.

## Enforcement

If any invariant is violated or any checklist item is unanswered do not proceed.
Report the violation and propose a corrective design before continuing.
