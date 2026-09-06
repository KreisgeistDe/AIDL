# Repository Agent Instructions

## Repository as Source of Truth

The current project branch is the durable source of truth for AIDL source code, tests, specifications, documentation, and accepted architecture decisions. Conversation memory and agent reports are never substitutes for the current repository state.

Operational agent state is separate: dispatches, results, handoffs, blockers, validation, pull-request, CI, merge, and scheduling state belong exclusively to the append-only transport on `agents/channel`.

Persist conclusions in project documentation or ADRs when they are durable project knowledge. Do not store chat transcripts, hidden reasoning, chronological work logs, or operational workflow state on project branches.

## Starting a Task

Before making changes:

1. Read this `AGENTS.md`.
2. Read the explicit channel dispatch that assigned the task.
3. Inspect the current `main` and any expressly named project PR head.
4. Inspect only the source, tests, specifications, documentation, and accepted ADRs relevant to the task.

`plugins/intellij/AGENTS.md` adds plugin-specific rules for work under `plugins/intellij/`.

## Conflict Priority

When sources disagree, use this priority:

1. Current source code and tests
2. The explicit append-only channel dispatch
3. Accepted architecture decisions
4. Current specification and documentation
5. Conversation context

Escalate genuine semantic or specification conflicts rather than silently choosing a new language meaning.

## Project-Branch Write Boundary

Project branches must not contain `.ai/**`. Agents MUST NOT add or recreate any path under `.ai/**` on `main`, feature branches, or project pull requests.

This prohibition applies to every agent role and includes task status, context, backlog, handoff, validation, PR, CI, merge, and integration data. Operational updates must be written only as new append-only message or orchestration records on `agents/channel`.

Workflow maintenance for `.ai/**` itself must use a dedicated pull request whose base is `agents/channel`; it must never be bundled into a project pull request targeting `main`.

## Change Discipline

- Follow the milestone order in `TODO.md`; optimize for measurable progress toward the next milestone acceptance criterion.
- Treat compiler/parser behavior as independent of IntelliJ PSI. IDE behavior must not become the semantic source of truth.
- Choose one coherent, semantically complete work package that a single agent can implement, review, and validate in one development cycle. Prefer completing a roadmap item or usable vertical capability over minimizing diff size.
- Bundle technically coupled implementation, tests, and durable project documentation in one PR. Split only for independent deliverability, materially different risk, an external blocker, reviewability, or objectively excessive scope.
- Do not refactor unrelated areas or change language semantics without an explicit task or architecture decision.
- Generated outputs are not manual repair targets; fix the source DSL, semantic model, adapter, or generator instead.
- Do not bypass or weaken the project-branch `.ai/**` protection.

## Workflow Ownership

### Implementation, fix, and recovery

- These agents own permitted project mutations outside `.ai/**`.
- Before requesting integration, make the project PR describe the intended post-merge project state through implementation, tests, specifications, documentation, ADRs, and `TODO.md` where appropriate.
- Persist the result, validation evidence, blockers, and next operational step exclusively on `agents/channel`.

### Validation, review, and integration

- Validation and review agents are read-only gates. They do not modify the project PR head.
- If validation or consistency fails, report the exact defect through the channel and return the same PR to an implementation or fix agent.
- An integration agent verifies the unchanged final head against current `main`, required CI, reviews, protection, scope, and the absence of `.ai/**` changes; then it squash-merges and verifies the resulting commit and push CI.
- PR number, head SHA, merge SHA, CI details, live merge status, and handoff state belong in the channel result JSON.

## Finishing a Task

Before completion:

- Validate the change and run relevant tests, or inspect available GitHub CI status when local execution is unavailable.
- Confirm that the project diff contains no `.ai/**` mutation.
- Update durable project documentation, accepted ADRs, specifications, or `TODO.md` only when the implemented project state requires it.
- Persist the complete operational result as the dispatch-correlated append-only `result.json` on `agents/channel`.
- Keep strings short and factual; persist conclusions, not deliberation.

The central rule is: **project knowledge lives with the project; operational agent state lives on the channel.**
