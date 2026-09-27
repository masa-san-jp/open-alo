# Canonical minimal ALO

This example demonstrates the **core ALO semantics**, not merely an execution workflow.

## Four required concepts

- `mainObj`: the learning coach as the whole object
- `subObjList`: comprehension analyzer and explanation engine
- `State`: level, progress, memory, active status
- `managerObj`: reads input, coordinates objects, optionally calls Jev, updates State, and emits output

## Conceptual diagram

```mermaid
flowchart TD
    I[Input]
    MGR[managerObj<br/>learning_coach_manager]
    MAIN[mainObj<br/>learning_coach]
    SUB1[subObj<br/>comprehension_analyzer]
    SUB2[subObj<br/>explanation_engine]
    STATE[State]
    JEV[Jev Noul<br/>optional calculation]
    O[Output]

    I --> MGR
    MGR --> MAIN
    MAIN --> SUB1
    MAIN --> SUB2
    MGR --> STATE
    STATE --> MGR
    MGR --> SUB1
    SUB1 --> JEV
    JEV --> MGR
    MGR --> SUB2
    MGR --> O
```

The Jev node is optional execution detail. Removing Jev does not remove the ALO.

## Reproducibility

A run should record the exact ALO version, input, State before, manager steps, sub-objects used, Jev request/result when used, deterministic calculations, State after, and output.
