# Open ALO Specification — Canonical Draft 0.2

> **Normative SSOT**
>
> This document defines what an ALO is. Implementations, schemas, graph formats, CLI behavior, Studio behavior, and Jev integration MUST conform to this document.
>
> Draft 0.1 incorrectly reduced ALO to a probabilistic workflow DSL. That interpretation is superseded by this document.

## 1. Definition

ALO (Abstract Language Object) is a way to represent a real-world concept, system, role, or dynamic situation as a language-defined object that an LLM can interpret and operate.

ALO combines:

- the flexibility of natural language;
- explicit object structure;
- explicit state;
- an explicit manager that interprets input, coordinates objects, updates state, and produces output.

An ALO is **not** identical to a decision graph, a rules engine, a Jev workflow, or a YAML schema.

Those are representations or execution mechanisms for an ALO.

## 2. Canonical conceptual model

Every ALO is built around four core components.

### 2.1 `mainObj`

The top-level object that represents the whole system or concept.

It defines:

- what the ALO is;
- its purpose;
- its scope;
- its high-level responsibilities.

Example:

```yaml
mainObj:
  id: learning_coach
  name: Programming Learning Coach
  purpose: Support a learner while maintaining an explicit learning state.
```

### 2.2 `subObjList`

The child objects that compose the `mainObj`.

Each sub-object represents a meaningful function, concept, role, or capability inside the ALO.

Example:

```yaml
subObjList:
  - id: comprehension_analyzer
    purpose: Evaluate learner understanding.

  - id: motivation_manager
    purpose: Track and respond to learner motivation.

  - id: explanation_engine
    purpose: Produce explanations appropriate to the current state.
```

Sub-objects are part of the ALO's conceptual structure. They MUST NOT be replaced merely by decision nodes.

### 2.3 `State`

The explicit dynamic state held by the ALO and/or its objects.

State represents values that may change during interaction or simulation.

Example:

```yaml
State:
  level: 1
  progress: 0.0
  memory: []
  activeStatus: initializing
```

For reproducibility, implementations SHOULD additionally define types, allowed values, initialization rules, and update ownership.

### 2.4 `managerObj`

The execution and coordination object.

`managerObj` receives input and is responsible for:

1. interpreting the input;
2. determining which objects and state are relevant;
3. coordinating `mainObj` and `subObjList`;
4. performing or requesting required judgments/calculations;
5. updating `State` according to declared rules;
6. producing output;
7. exposing enough execution information to reproduce or inspect the result.

The manager may use deterministic code, an LLM, Jev, or other tools internally. These mechanisms do not replace `managerObj`; they implement parts of its work.

## 3. Canonical relationship

```text
                      ALO
                       │
                ┌──────┴──────┐
                │             │
             mainObj        State
                │             ▲
                │ contains    │ reads / updates
                ▼             │
           subObjList         │
                │             │
                └──────┬──────┘
                       │ coordinates
                       ▼
                  managerObj
                       ▲
                       │
                     Input
                       │
                       ▼
                     Output
```

The four-component model is mandatory conceptual vocabulary for Open ALO.

## 4. Three layers of Open ALO

Open ALO provides three distinct layers.

### Layer A — ALO Prompt

The language representation that tells an LLM what the object is and how it behaves.

This is the primary authoring concern.

### Layer B — ALO Diagram

A visual projection of the ALO's object structure, state, relationships, manager flow, and optionally execution/calculation nodes.

The diagram is derived from the ALO definition. It does not redefine it.

### Layer C — Jev Calculation

An optional execution mechanism used by `managerObj` for typed probabilistic judgments.

Jev is not the definition of ALO.

The relationship is:

```text
ALO Prompt
   ↓
ALO object model
   ├──→ ALO Diagram
   │
   └──→ managerObj execution
            ├── deterministic processing
            ├── LLM processing
            └── Jev calculation
```

## 5. ALO prompt authoring format

The canonical prompt representation MUST make the four components visible.

Minimum prompt:

```markdown
# ALO

You are operating the following Abstract Language Object.

## mainObj
- id: <id>
- purpose: <purpose>
- responsibilities:
  - ...

## subObjList
### <subObj id>
- purpose: ...
- responsibilities:
  - ...

## State
- <state key>: <initial/current value>

## managerObj
For every input:
1. Read the input.
2. Read the current State.
3. Select the relevant mainObj/subObj responsibilities.
4. Perform the declared analyses/calculations.
5. Update State only according to the declared update rules.
6. Produce the declared output.
7. Expose the resulting State and execution trace when requested.

## Input
<runtime input>
```

An implementation MAY generate this prompt from YAML/JSON, but the generated prompt MUST preserve these semantics.

## 6. Structured serialization

For tooling and reproducibility, an ALO MAY be serialized in YAML or JSON.

The canonical serialized form MUST preserve the same conceptual model:

```yaml
alo:
  spec_version: "0.2"
  id: example
  version: "0.1.0"

  mainObj:
    id: example
    purpose: ...

  subObjList:
    - id: sub_1
      purpose: ...

  State:
    ...

  managerObj:
    input: ...
    process:
      - ...
    state_updates:
      - ...
    output: ...
```

Additional fields are allowed, but an implementation MUST NOT redefine ALO so that these four components disappear.

## 7. Reproducibility requirements

A reproducible ALO implementation SHOULD make the following explicit:

- ALO version;
- complete prompt or canonical serialization;
- initial/current State;
- input;
- manager process;
- sub-object selection or use;
- external calls;
- Jev questions/results when used;
- deterministic calculations;
- State changes;
- final output.

The same ALO version and the same recorded execution inputs should be inspectable and comparable across runs.

Reproducibility does not require a stochastic model to emit byte-identical prose. It requires the system to expose the structure, state, calculations, and decisions that produced the result.

## 8. ALO Diagram

The diagram is a projection of the conceptual model.

Minimum semantic node types:

- `MAIN_OBJECT`
- `SUB_OBJECT`
- `STATE`
- `MANAGER`
- `INPUT`
- `OUTPUT`

Optional execution nodes:

- `JEV_NOUL`
- `JEV_CHOICE`
- `JEV_SCORE`
- `DETERMINISTIC_CALC`
- `RULE`
- `EXTERNAL_TOOL`

Minimum semantic relationships:

- `CONTAINS`
- `COORDINATES`
- `READS_STATE`
- `UPDATES_STATE`
- `RECEIVES`
- `EMITS`
- `CALLS`

A graph that contains only input/decision/rule/output nodes but cannot represent `mainObj`, `subObjList`, `State`, and `managerObj` is NOT a complete ALO diagram.

## 9. Jev calculation

Jev is an optional calculation/judgment mechanism inside `managerObj`.

Use Jev when the manager requires an ambiguous semantic judgment that benefits from a typed probability.

Mapping:

| Jev primitive | Use |
| --- | --- |
| Noul | binary / yes-no judgment |
| Choice | choose among declared alternatives |
| Score | degree, ranking, or scalar judgment |

Example:

```text
managerObj
  ↓
"Does the learner understand this concept?"
  ↓
Jev Noul
  ↓
P(true)=0.88
  ↓
managerObj applies declared update rule
  ↓
State.progress changes
```

Jev MUST NOT replace the object model.

Jev SHOULD NOT be used for deterministic arithmetic, date arithmetic, exact matching, or other operations that normal code can reproduce exactly.

## 10. State updates

Conceptually, `managerObj` owns State transition.

An implementation MAY delegate the mechanical application of an explicit state-update rule to a rule engine.

Therefore:

```text
managerObj declares/coordinates the transition
runtime/rule engine may apply it deterministically
```

This preserves the original ALO model while allowing reproducible execution.

## 11. Dynamic extension

The original ALO approach may allow new sub-objects to be added during interaction.

For reproducible implementations, dynamic extension MUST be explicit.

A dynamically created object MUST have:

- a unique ID;
- creation reason;
- parent relationship;
- creation time/run;
- definition;
- version or run-local identity.

Silent mutation of `subObjList` is not permitted in reproducibility mode.

## 12. Conformance rule

Any Open ALO implementation claiming core conformance MUST demonstrate that it can represent and preserve:

1. `mainObj`;
2. `subObjList`;
3. `State`;
4. `managerObj`;
5. the relationships among them;
6. input-to-manager execution;
7. state evolution;
8. output generation.

Jev support, Mermaid generation, CLI commands, packaging, and hosted services are optional capabilities layered on top of this core definition.


## 13. Original ALO semantics that MUST be preserved

The canonical four-component model is not only a static schema. The original ALO concept also includes the following behavioral semantics.

### 13.1 managerObj execution cycle

For each input, managerObj conceptually performs this cycle:

1. receive and interpret the input;
2. inspect the current State;
3. identify the relevant mainObj/subObj responsibilities;
4. perform required analysis, judgment, simulation, calculation, or tool use;
5. determine a State transition;
6. update State;
7. generate the response/action/output;
8. optionally expose the resulting State and execution trace.

An implementation MAY realize these steps with an LLM, deterministic code, Jev, other tools, or a combination of them.

### 13.2 Initial State

ALO definitions MAY specify explicit initial State.

Initial State is part of the ALO definition and MUST be distinguishable from runtime State.

### 13.3 Initial Output / startup behavior

An ALO MAY define startup behavior before ordinary interaction begins, for example:

- render the initial State;
- greet the user;
- ask the first question;
- initialize a task or simulation.

Startup behavior belongs to managerObj and MUST be representable when present.

### 13.4 State dashboard

A State dashboard is a presentation of State, not State itself.

ALO MAY request State to be displayed after each turn for debugging, inspection, or interaction. The canonical serialized State remains the source of truth.

### 13.5 Dynamic sub-object extension

ALO MAY allow managerObj to create or attach new sub-objects during interaction.

Open ALO MUST NOT prohibit this capability.

For reproducibility, dynamic changes MUST be explicit and recorded with at least:

- object ID;
- parent relationship;
- definition;
- creation reason;
- run identity;
- resulting object graph version or run-local mutation record.

### 13.6 Natural-language behavior is first-class

ALO is not limited to fields that can be reduced to deterministic code.

Responsibilities, behavioral instructions, interpretation criteria, response-generation instructions, and simulation semantics MAY remain natural-language definitions executed by an LLM.

The reproducibility layer exists to make those definitions, inputs, State, external judgments, and mutations inspectable. It MUST NOT erase the language-object nature of ALO.

## 14. Execution profiles

Open ALO distinguishes the conceptual model from execution strictness.

### 14.1 Interactive profile

Optimized for flexible LLM interaction.

managerObj MAY perform language-based analysis and propose State updates directly, subject to declared constraints.

### 14.2 Reproducible profile

Optimized for inspection, comparison, and repeatability.

The runtime SHOULD record:

- exact ALO definition/prompt;
- input;
- State before;
- manager steps;
- sub-objects used;
- model/provider calls;
- Jev calls;
- deterministic calculations;
- proposed and applied State updates;
- State after;
- output.

Where possible, deterministic calculations and mechanical update application SHOULD be separated from probabilistic judgment.

Both profiles implement the same ALO conceptual model.
