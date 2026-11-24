# Spec <nnn>: <Title>

| Field | Value |
|---|---|
| Status | Draft / **frozen** / implemented |
| Risk | low / medium / high |
| Frozen on | YYYY-MM-DD |

## Goal
One to three sentences: what can a user do afterwards that was not possible before?

## Non-goals
What is explicitly **not** part of this spec. Prevents scope creep.

## Context
What the implementer needs to know: domain background, relevant data fields with exact
column names, peculiarities of the data, existing building blocks in the code.

## Acceptance criteria
Every criterion is **machine-checkable** and gets at least one test.
Form: Given / When / Then.

- **AC1** Given … When … Then …
- **AC2** …

## File plan
Which files are created or changed, with one sentence of purpose per file.

| File | Purpose |
|---|---|
| `src/...` | … |
| `tests/...` | … |

## Breakdown (proposal)
Small increments, each at most about 200 lines of diff, each testable on its own.

1. …
2. …

## Risks and open points
What can go wrong, and what to do when unclear (block and ask).

## Acceptance
How is it verified at the end that the spec is fulfilled? Reference to the holdout scenarios,
which live outside this repo.
