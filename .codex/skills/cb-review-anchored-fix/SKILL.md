---
name: cb-review-anchored-fix
description: Review response skill require checking related sources specs code tests plans before applying changes not only requested fixes ask questions on doubts review comment PR feedback 指摘 レビュー対応 修正 反映 仕様 確認 関連 ソース テスト 整合
metadata:
  short-description: Handle review feedback with source checks and decision questions not patch only.
---

## Selection note

Skill selection may be automatic or explicit depending on the environment.
This document defines mandatory behavior when this skill is selected.
For review responses invoke this skill by name to guarantee execution.

## Purpose

Prevent patch only review responses.
Ensure changes are consistent with related specifications sources and existing implementation.
Require explicit questions when review feedback is ambiguous or conflicts with sources.

## When to use

Use this skill when responding to review feedback PR comments or requested changes.
Use this skill when the user says review feedback comments 指摘 直して 修正対応 address review.
Use this skill when preparing follow up commits after code review.

## Core rules

Do not implement only what is explicitly requested if it creates inconsistency.
Always check relevant sources and update the smallest coherent set of artifacts.
If there is uncertainty conflict or missing context you must ask questions before finalizing.

## Required sources to check

You must check all applicable categories below.

Review input sources.
The exact review comments and the diff context.

Specification sources.
Backend specs requirements integration boundaries UI specs if relevant.

Implementation plan sources.
Plans for jobs audit security integration database.

Existing implementation sources.
Relevant modules and call sites.

Tests and contracts.
Schemas OpenAPI tests and fixtures.

If a category is not applicable state Not applicable and explain why.

## Mandatory output format

Your output must contain exactly five sections.
Review intent summary.
Checked sources.
Proposed changes.
Questions and disagreements.
Acceptance checklist.

Do not add any other sections.

## Review intent summary requirements

Restate the review request in your own words as a single coherent intent.
List what is explicitly requested and what is implied.

## Checked sources requirements

List what you reviewed using concrete identifiers such as file path document name and section.
Include at least two sources when possible.
If you cannot access sources state what is missing.

## Proposed changes requirements

Propose a minimal coherent change set.
Include any additional necessary fixes discovered by source checking.
State why each change is required and what it aligns with.

## Questions and disagreements requirements

If anything is ambiguous conflicting or risky you must ask questions.
If you disagree with a review comment you must state the disagreement and the evidence.
Questions must be direct and decision oriented.

If there are no questions write No questions.

## Acceptance checklist requirements

Provide a checklist of verifiable completion criteria.
Include code change tests and documentation updates if applicable.
Checklist items must be testable and phrased as complete sentences.

## Enforcement

If Checked sources is empty you must not proceed.
If you have questions you must not pretend certainty.
If sources contradict the review request you must surface the conflict and ask for a decision.

## Final rule

Review response is successful only when the system remains consistent with its sources.
Patch only compliance is failure.
