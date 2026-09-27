# Open ALO packaging

Open ALO Draft 0.1 packages are plain, readable directories intended to remain
easy to inspect, diff, fork, and copy. A package contains an
`alo-package.json` manifest and the ALO document named by its `entry` field.

## Manifest

The manifest has these required fields:

- `name`: an identifier matching `^[A-Za-z][A-Za-z0-9_-]*$`.
- `version`: a non-empty package version string.
- `spec_version`: exactly `"0.1"`.
- `entry`: a relative path to the package's main ALO YAML or JSON document.

It may also contain non-empty `description` and `homepage` strings. The
manifest is described by [`schemas/alo-package.schema.json`](../schemas/alo-package.schema.json).
The referenced ALO document is validated with the normal Draft 0.1 validator.

## Commands

Build a validated package directory, excluding VCS directories, dotfiles, and
`__pycache__`:

```bash
alo package build examples/canonical-minimal --out build/
```

Install from a Git repository into a destination directory. A local filesystem
path works as the repository source, so this workflow does not require a
network:

```bash
alo package install ./some-alo-repository --dest packages/
alo package install ./some-alo-repository --dest packages/ --ref main
alo package install ./some-alo-repository --dest packages/ --subdir packages/example
```

Search a registry index and generate a compatibility badge:

```bash
alo package search registry.json triage
alo package badge examples/canonical-minimal/alo-package.json
alo package badge examples/canonical-minimal/alo.yaml
```

## Optional local registry/discovery sketch

The registry format is deliberately only an optional local/offline discovery
sketch, not a hosted service or a network protocol requirement. A registry is
a JSON object with an `entries` array. Each entry has `name`, `description`,
`source`, and `latest_version`; `source` can be a local path or any source
reference understood by a separate installer. The format is described by
[`schemas/alo-registry.schema.json`](../schemas/alo-registry.schema.json).

All validation, package builds, registry searches, and tests can run offline.
