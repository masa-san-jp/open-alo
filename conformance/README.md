# Draft 0.1 conformance fixtures

This directory is a small suite of ALO documents with golden/pinned Graph IR
and Run Record fixtures. It is intended to help verify Draft 0.1 conformance
in any implementation, not only in this reference implementation.

Golden Run Record comparisons intentionally exclude only `run_id` and
`timestamp`. Both fields are inherently non-deterministic per run; every
other field is part of the pinned behavior and remains comparable.
