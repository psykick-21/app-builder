# Intent Interpreter — Detailed Design Specification

## 1. Purpose (Authoritative Statement)

The **Intent Interpreter** is the *single authoritative component* responsible for translating human language into a **stable, structured intent specification** that the rest of the system can deterministically consume.

It is intentionally **narrow in scope**.

> Its sole responsibility is to convert *human ambiguity* into *machine certainty*.

All downstream components (planner, orchestrator, generators) treat the intent as **read-only input**.

---

## 2. Position in the Overall Architecture

- Implemented as **one node** inside the global LangGraph workflow
- Executed:
  - Once during initial application creation
  - Again whenever user feedback requires semantic changes

The Intent Interpreter is:
- The **first semantic gate** in the system
- The **only component allowed to create or modify `intent.json`**

No other agent or module is permitted to mutate intent artifacts.

---

## 3. Design Principles

The Intent Interpreter follows these strict principles:

1. **Single-writer rule**
   - Only this component can write intent artifacts

2. **Snapshot-based intent**
   - Always outputs a *complete intent document*
   - Never emits partial updates or deltas

3. **Schema-first enforcement**
   - Intent validity is enforced by Pydantic, not LLM trust

4. **Minimal inference**
   - No speculative features
   - No architectural assumptions

5. **Deterministic evolution**
   - Intent evolves only in response to explicit user feedback

---

## 4. Operating Modes

The Intent Interpreter operates in **two explicit modes**. The orchestrator determines which mode to invoke.

---

### 4.1 Mode 1 — CREATE (Initial Intent Generation)

#### Trigger Condition
- No existing intent is present in the orchestrator state

#### Inputs
```python
raw_user_input: str
existing_intent: None
```

#### Example Input
```text
"Build a simple task management app where I can create, update, and delete tasks. Each task should have a title and description."
```

#### Semantic Responsibility
- Extract core domain concepts
- Identify primary entities
- Identify supported operations
- Capture UI expectations and constraints

No defaults are invented by the LLM; defaults are filled later by Pydantic.

---

### 4.2 Mode 2 — MODIFY (Intent Evolution via User Feedback)

#### Trigger Condition
- An existing intent is present
- User provides feedback

#### Inputs
```python
existing_intent: dict
user_feedback: str
```

#### Example Input
```text
"Add due dates to tasks"
```

#### Semantic Responsibility
- Modify the existing intent **minimally**
- Preserve all unrelated entities, fields, and assumptions
- Avoid renaming or restructuring unless explicitly requested

The output is still a **complete intent snapshot**, not a delta.

---

## 5. Output Contract

### 5.1 Canonical Output Artifact

```
generated_apps/<app_id>/spec/intent.json
```

Each successful run:
- Overwrites the previous `intent.json`
- Appends a human-readable summary entry to `changes.log`

---

### 5.2 Logical Intent Schema

```json
{
  "app_summary": "string",
  "app_category": "crud_app",

  "primary_entities": {
    "<EntityName>": {
      "description": "string",
      "fields": {
        "<field_name>": {
          "type": "string | integer | boolean | date",
          "required": true
        }
      }
    }
  },

  "operations": {
    "<EntityName>": ["create", "read", "update", "delete"]
  },

  "ui_expectations": {
    "complexity": "basic",
    "interaction_style": "form_and_list"
  },

  "assumptions": ["string"],
  "non_goals": ["string"]
}
```

This schema is **stable across the entire system**.

---

## 6. Structured Output Enforcement

### 6.1 LLM Output Constraints

The Intent Interpreter **must use structured output enforcement**, such as:
- JSON schema binding
- Function calling
- Tool invocation with typed outputs

Free-form text output is **not permitted**.

---

### 6.2 Pydantic as the Source of Truth

A Pydantic model defines the canonical intent schema.

Pydantic is responsible for:
- Filling default values
- Enforcing required fields
- Enforcing type correctness
- Rejecting malformed or incomplete outputs

Example default behaviors:
- `ui_expectations.complexity = "basic"`
- `assumptions = ["Single-user", "Local execution"]`

If validation fails:
- The graph fails fast
- An optional single retry may be attempted with reinforced constraints

No LLM-based normalization or correction occurs after validation.

---

## 7. Internal Execution Flow (Single-Node)

The Intent Interpreter is implemented as **one LangGraph node**.

```
Raw Input (or Feedback)
        ↓
LLM Call (Structured Output)
        ↓
Pydantic Validation + Default Filling
        ↓
Validated Intent Object
        ↓
Persist intent.json + update graph state
```

There are **no sub-nodes** inside this component for MVP simplicity.

---

## 8. Determinism & Stability Guarantees

The Intent Interpreter is expected to maintain:

- **Structural determinism**
  - Same schema across runs

- **Semantic stability**
  - No renaming of entities or fields unless requested

- **Idempotent evolution**
  - Given the same existing intent and feedback, output should be structurally equivalent

This stability is critical for downstream orchestration and impact analysis.

---

## 9. Explicit Non-Responsibilities

The Intent Interpreter **must not**:

- Choose backend or frontend technologies
- Decide file names or module paths
- Perform impact analysis
- Modify architecture or code artifacts
- Infer features not explicitly requested
- Resolve ambiguities silently

Any uncertainty must be recorded as an assumption rather than inferred.

---

## 10. Why This Design Is Correct

This design:
- Centralizes semantic ownership
- Eliminates hidden coupling between agents
- Enables deterministic planning
- Makes feedback-driven iteration safe and explainable

By enforcing strict boundaries, the Intent Interpreter ensures that all creativity is *front-loaded*, while all execution remains *predictable*.

---

## 11. One-Paragraph Summary (For README / Evaluation)

The Intent Interpreter is a single LangGraph node responsible for creating and evolving a structured application intent from natural language. It operates in create and modify modes, enforces schema correctness via Pydantic with default filling, outputs complete intent snapshots, and is the only component permitted to mutate intent artifacts. This strict separation of semantic interpretation from planning and execution enables deterministic orchestration, selective regeneration, and robust user-driven iteration.

