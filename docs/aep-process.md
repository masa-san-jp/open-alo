# ALO Enhancement Proposal (AEP) Process

This document defines the process referenced by [`CONTRIBUTING.md`](../CONTRIBUTING.md)
for substantial changes to the Open ALO specification, Graph IR, Run Record
format, or Decision Provider interface.

## When an AEP is required

Use the lightweight GitHub issue/PR workflow in `CONTRIBUTING.md` for bug
fixes, documentation, additive tooling (CLI subcommands, examples, test
fixtures), and implementation-only changes that do not alter the Draft 0.1
data model.

Open an AEP for anything that changes what a *conforming implementation*
must do, including:

- adding, removing, or changing the meaning of a top-level `alo.*` field;
- changing `schemas/alo.schema.json` in a way that rejects previously valid
  documents, or accepts a new required construct;
- adding or changing a Graph IR node or edge type (`docs/graph-ir.md`);
- adding or changing a Run Record field (`docs/spec.md` section 12);
- changing the `DecisionProvider` interface (`packages/providers/base.py`);
- changing rule-evaluation semantics (priority ordering, first-match-wins,
  `no_previous_rule_matched`, stop conditions).

When in doubt, open an AEP. A proposal that turns out to be small is cheap to
close as "accepted, implement directly"; a spec change made without one is
expensive to unwind once implementations depend on it.

## Proposal format

Copy [`aeps/0000-template.md`](../aeps/0000-template.md) to
`aeps/NNNN-short-title.md`, where `NNNN` is the next unused four-digit number
(check open PRs too, not just merged AEPs, to avoid collisions). Fill in:

1. **Problem** — what can't be expressed or verified today, with a concrete
   example ALO or Run Record fragment where possible.
2. **Proposed change** — the exact field/schema/interface delta.
3. **Alternatives** — at least one alternative considered and why it was
   rejected, including "do nothing."
4. **Backward compatibility** — whether existing valid ALO documents and
   existing Run Records remain valid; if not, what breaks and why that is
   acceptable at the current spec version.
5. **Conformance impact** — which `conformance/canonical-cases/` fixtures need to be
   added or updated, and whether `packages/core`, `packages/compiler`, or
   `packages/runtime` need corresponding changes.

## Lifecycle

An AEP moves through these statuses, recorded in its front matter:

1. **Draft** — opened as a PR adding `aeps/NNNN-*.md` with `status: draft`.
   Discussion happens on the PR.
2. **Accepted** — the decision-maker (see below) approves the direction.
   The author (or anyone) may now implement it; the schema/spec/code change
   normally lands as a separate PR that references the AEP number.
3. **Implemented** — the reference implementation, schema, and at least one
   `conformance/` fixture reflect the change. The AEP PR and the
   implementation PR may be the same PR for small changes.
4. **Rejected** or **Withdrawn** — closed with a one-line reason recorded in
   the AEP file itself (do not delete rejected AEPs; they prevent re-litigating
   settled questions without new information).

## Decision authority

Open ALO is currently pre-alpha with a single maintainer. Until there are
multiple maintainers with merge access:

- the repository owner decides Accepted/Rejected, informed by PR discussion.

Once there are multiple maintainers, this section should itself be updated
via an AEP, but the following is the intended default: lazy consensus among
maintainers (no sustained objection within a stated review window), escalating
to the repository owner only if maintainers disagree and cannot converge.

This process document deliberately does not create a foundation, a voting
body, or a formal steering committee — that would be over-engineering
governance for a pre-alpha, single-maintainer project. Revisit this section
if and when the contributor base grows enough to need it.

## Explicitly out of scope for this process

- **License selection** — tracked directly in `README.md` ("TBD before the
  first tagged release"), not routed through an AEP.
- **Jev-specific behavior** — Jev is one Decision Provider implementation
  among several (see `docs/architecture.md`); changes scoped only to
  `packages/providers/jev.py` and not to the provider-neutral interface do
  not require an AEP.
