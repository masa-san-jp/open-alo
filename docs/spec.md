# Open ALO Specification — Draft 0.1

## 1. Scope

This document defines the minimum interoperable representation of an Abstract Language Object (ALO).

An ALO describes a workflow using explicit inputs, explicit state, probabilistic decisions, deterministic derived values and rules, explicit outputs, and explicit stop conditions.

An ALO is not a prompt persona and is not tied to a particular model provider.

## 2. Processing model

```text
Input
  ↓
Normalize
  ↓
State(t)
  ↓
Decision nodes
  ↓
Typed probabilistic results
  ↓
Deterministic rules
  ↓
State(t+1)
  ↓
Output
```

Decision providers may read state. They do not mutate state.

## 3. Required top-level fields

```yaml
alo:
  spec_version:
  id:
  version:
  purpose:
  inputs:
  state_schema:
  decisions:
  transition_rules:
  outputs:
```

Optional fields include `scope`, `objects`, `derived_values`, `thresholds`, `stop_conditions`, and `invariants`.

## 4. Inputs

Every input MUST declare a type. Missing required input MUST be rejected rather than inferred.

## 5. State

Every state field MUST define its type, initial value, and update authority. A Decision Provider MUST NOT directly mutate state.

## 6. Decision types

Open ALO defines three provider-neutral decision primitives.

### 6.1 binary

A yes/no semantic judgment.

```yaml
p_true: 0.91
p_false: 0.09
```

Jev mapping: **Noul**.

### 6.2 categorical

A choice from a fixed set declared by the ALO.

```yaml
probabilities:
  technical: 0.80
  billing: 0.15
  other: 0.05
```

Jev mapping: **Choice**.

### 6.3 scalar

A degree on a declared scale.

```yaml
score: 0.82
confidence: 0.91
```

Jev mapping: **Score**.

## 7. Decision constraints

1. One decision node represents one judgment.
2. Categorical options are fixed before execution.
3. Arithmetic and date operations are not delegated to a decision provider.
4. Explicit business rules are evaluated deterministically.
5. Uncertainty is retained until a rule converts it to an action.
6. Only the minimum required state is passed to a decision.

## 8. Derived values

Derived values are deterministic. The exact expression language is not frozen in draft 0.1.

## 9. Transition rules

Rules consume inputs, state, derived values, and decision results. If multiple rules can update the same field, execution order MUST be explicit.

## 10. Stop conditions

ALO runtimes MUST prevent implicit unbounded loops.

Typical stop conditions include input error, terminal state, human review required, and maximum iteration count.

## 11. Graph IR

Initial node types:

- `INPUT`
- `STATE`
- `DERIVE`
- `DECISION_BINARY`
- `DECISION_CATEGORICAL`
- `DECISION_SCALAR`
- `RULE`
- `ACTION`
- `OUTPUT`
- `STOP`

Initial edge types:

- `READS`
- `DEPENDS_ON`
- `GATES`
- `UPDATES`
- `EMITS`
- `STOPS`

The diagram is a generated view of Graph IR, not a second source of truth.

## 12. Reproducibility record

A runtime SHOULD be able to persist:

```yaml
run:
  run_id:
  timestamp:
  alo_id:
  alo_version:
  provider:
  provider_model:
  provider_config:
  threshold_version:
  normalized_input:
  state_before:
  decision_requests:
  decision_results:
  rule_trace:
  state_after:
  output:
  status:
```

## 13. Provider interface

The reference runtime will expose behavior equivalent to:

```python
class DecisionProvider:
    def binary(self, state, question): ...
    def categorical(self, state, question, options): ...
    def scalar(self, state, question, scale): ...
```

Implementations MAY use Jev, local LLMs, remote LLM APIs, deterministic mocks, or other systems.

## 14. Conformance

A conforming implementation can validate the supported ALO schema, compile it into equivalent Graph IR, preserve declared decision types, prevent provider-side state mutation, execute deterministic rules consistently, and emit a machine-readable run record.

A formal conformance suite will be added before 1.0.
