# Orchestrator — Detailed Design Specification

## 0. Purpose of This Document

This document defines the **Orchestrator**, the central control system that coordinates all agents, manages state, enforces execution order, handles validation loops, persists artifacts, and enables safe iteration through user feedback.

The Orchestrator is the **brain of the system**.

> Agents reason and generate.  
> Validators check.  
> **The Orchestrator decides.**

This document is intentionally exhaustive, as orchestration is the primary evaluation criterion of the assignment.

---

## 1. Core Responsibility (Authoritative Statement)

The **Orchestrator** is responsible for:
- Managing global execution state
- Invoking agents with correct context
- Persisting and versioning artifacts
- Enforcing execution order and dependencies
- Running validation and retry loops
- Handling user feedback and selective regeneration

The Orchestrator **does not**:
- Generate code
- Validate code logic
- Interpret natural language
- Make architectural decisions

Those responsibilities are delegated to specialized agents.

---

## 2. Position in the System

- Implemented as the **LangGraph root graph**
- Owns the global state object
- Controls all transitions and retries

All agents are executed *through* the Orchestrator.

---

## 3. Orchestrator Inputs

### 3.1 External Inputs (From UI / User)

```python
raw_user_input: str | None
user_feedback: str | None
```

Only one of these is non-null at a time.

---

### 3.2 Internal Persistent Artifacts

The Orchestrator loads and manages:
- `intent.json`
- `architecture.json`
- `code_map.json`
- `changes.log`

These artifacts live under:
```
generated_apps/<app_id>/spec/
```

Filesystem is treated as the **source of truth**.

---

### 3.3 Static System Configuration

- Agent Repository (code agents only)
- Validation rules
- Retry limits

These are loaded once at startup and treated as immutable.

---

## 4. Global Orchestrator State

The Orchestrator maintains a **typed, explicit state object**.

```python
class OrchestratorState(TypedDict):
    app_id: str
    raw_user_input: str | None
    user_feedback: str | None

    intent: dict | None
    architecture: dict | None

    execution_queue: list[dict]
    current_layer: str | None

    generated_files: list[str]
    validation_errors: list[dict]

    retry_counts: dict[str, int]
    status: Literal[
        "idle",
        "planning",
        "generating",
        "validating",
        "iterating",
        "completed",
        "failed"
    ]
```

### State Invariants
- Only the Orchestrator mutates state
- Agents receive read-only slices of state
- State changes are logged

---

## 5. Artifact Lifecycle Management

### 5.1 Application Directory Creation

On first run:
```
generated_apps/<app_id>/
├── spec/
├── backend/
├── frontend/
└── README.md
```

The Orchestrator creates this structure before any agent runs.

---

### 5.2 Intent Persistence

After Intent Interpreter execution:
- Intent is written to `spec/intent.json`
- Previous intent (if any) is overwritten
- A summary is appended to `changes.log`

---

### 5.3 Architecture Persistence

After Architect execution:
- Architecture is written to `spec/architecture.json`
- Validated for stability

---

### 5.4 Code Map Maintenance

The Orchestrator maintains `code_map.json`:

```json
{
  "backend_models": ["backend/models/task.py"],
  "backend_services": ["backend/services/task_service.py"],
  "backend_routes": ["backend/routes/task_routes.py"],
  "frontend_ui": ["frontend/app.py"]
}
```

Each code agent must report generated files, which are registered here.

---

## 6. Execution Flow (Initial Generation)

### Step 1 — Intent Interpretation

Input:
- `raw_user_input`

Action:
- Call Intent Interpreter

Output:
- Validated intent object

Persist:
- `intent.json`

---

### Step 2 — Architecture Planning

Input:
- `intent`
- `existing_architecture = None`

Action:
- Call Architect Agent

Output:
- Architecture plan

Persist:
- `architecture.json`

---

### Step 3 — Build Execution Queue

The Orchestrator constructs an execution queue from `architecture.execution_layers`, respecting dependencies.

Example:
```python
execution_queue = [
  "backend_models",
  "backend_services",
  "backend_routes",
  "backend_app",
  "frontend_ui"
]
```

---

### Step 4 — Layer-by-Layer Execution

For each layer in `execution_queue`:

#### 4.1 Code Generation
- Invoke corresponding code agent
- Pass:
  - intent slice
  - architecture layer config

#### 4.2 Artifact Registration
- Capture list of generated files
- Update `code_map.json`

#### 4.3 Validation
- Invoke Validation Agent
- Pass:
  - files for this layer
  - layer constraints

#### 4.4 Retry Logic
- If validation fails:
  - Increment retry count
  - Re-run generation (max N times)
- On repeated failure:
  - Abort execution

---

## 7. Validation & Retry Policy

### Retry Rules
- Max retries per layer: 2
- Retry is scoped to the failing layer only
- Successful layers are never re-run

All retry decisions are deterministic and logged.

---

## 8. Feedback & Iteration Flow

### Step 1 — Feedback Intake

Input:
```python
user_feedback: str
```

---

### Step 2 — Intent Evolution

Action:
- Call Intent Interpreter (MODIFY mode)

Persist:
- Updated `intent.json`

---

### Step 3 — Re-Plan Architecture

Action:
- Call Architect with:
  - new intent
  - existing architecture

Persist:
- Updated `architecture.json`

---

### Step 4 — Impact Analysis

The Orchestrator performs deterministic diffing:
- old intent vs new intent
- maps semantic changes → affected layers

Example:
```python
if entity_fields_changed:
    affected_layers = [
      "backend_models",
      "backend_services",
      "backend_routes",
      "frontend_ui"
    ]
```

---

### Step 5 — Selective Re-Execution

- Execution queue is rebuilt starting from the first affected layer
- Earlier layers are skipped

---

### Step 6 — Validation & Completion

- Validation runs only on regenerated layers
- On success:
  - Status = completed

---

## 9. LangGraph Implementation Model

Each execution layer is modeled as:

```
GenerateLayerX → ValidateLayerX
```

Transitions are controlled by Orchestrator routing functions.

---

## 10. Error Handling & Failure Modes

### Failure Types
- Intent validation failure
- Architecture stability violation
- Code validation failure

### Behavior
- Fail fast
- Surface precise error messages
- Do not partially commit broken state

---

## 11. Observability & Logging

The Orchestrator logs:
- State transitions
- Agent invocations
- Validation results
- Retry counts

Logs are:
- Human-readable
- Persisted alongside artifacts

---

## 12. Determinism Guarantees

The Orchestrator guarantees:
- Same inputs → same execution order
- Same artifacts → same regeneration behavior
- No hidden LLM state

---

## 13. Explicit Non-Responsibilities

The Orchestrator does not:
- Generate or validate code
- Interpret language
- Modify agent logic
- Perform schema inference

---

## 14. Why This Design Is Correct

This design:
- Makes orchestration explicit and inspectable
- Enables safe, partial regeneration
- Prevents cascading failures
- Demonstrates true agentic control

---

## 15. One-Paragraph Summary (For README / Evaluation)

The Orchestrator is the central control layer implemented as a LangGraph workflow that manages state, artifacts, execution order, validation loops, and feedback-driven iteration. It invokes agents deterministically, persists all intermediate artifacts, performs impact analysis for selective regeneration, and enforces strict retry and validation policies. This design separates reasoning from control, enabling predictable, inspectable, and extensible agentic application generation.

