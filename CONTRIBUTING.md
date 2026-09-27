# Contributing to Open ALO

Open ALO is intended to be an open, forkable specification and reference implementation.

## Before contributing

Please preserve these invariants:

- the ALO specification is provider-neutral;
- Jev is an adapter, not a protocol dependency;
- diagrams are generated from machine-readable graph data;
- decision providers do not mutate state;
- deterministic rules stay outside probabilistic providers;
- local/offline validation and graph generation remain possible.

## Proposed workflow

1. Open an issue describing the behavior or specification change.
2. For schema or protocol changes, include examples and compatibility impact.
3. Add or update conformance tests with implementation changes.
4. Keep generated artifacts out of the source of truth unless explicitly required.
5. Submit a focused pull request.

## Specification changes

Substantial specification changes use the ALO Enhancement Proposal (AEP)
process defined in [`docs/aep-process.md`](docs/aep-process.md). Start from
[`aeps/0000-template.md`](aeps/0000-template.md).

## Development status

The repository is pre-alpha. Public APIs and schemas may change before 1.0.
