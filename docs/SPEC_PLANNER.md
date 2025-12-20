# Spec Planner — Technical Design & Documentation

## 1. Purpose and Scope

The **Spec Planner** is a core reasoning component responsible for converting **Intent + Architecture** into **explicit, layer-specific execution specifications** ("specs") that can be consumed by coding agents.

The Spec Planner answers the question:

> *Given a fixed intent and a fixed architecture, what exactly must be built inside each layer?*

It does **not** write code and does **not** modify intent or architecture. It produces **structured, machine-readable plans** that eliminate ambiguity for code generation.

---

## 2. Position in the System Pipeline

```
User Prompt
   ↓
Intent Interpreter (LLM)
   ↓
intent.json
   ↓
Architect / Planner (LLM)
   ↓
architecture.json
   ↓
Spec Planner (LLM + Deterministic Validators)
   ↓
layer_specs/*.json
   ↓
Coding Agents (LLMs)
   ↓
Generated Code
```

The Spec Planner is the **last reasoning step** before code generation begins.

---

## 3. Why the Spec Planner Exists

Architecture defines **structure**, not **content**.

Example architectural layer:

```json
{
  "id": "backend_services",
  "generator": "BackendServiceAgent"
}
```

This does not specify:
- Which functions exist
- Function names or signatures
- Which entities they operate on
- Which operations are supported

Without an explicit planning step:
- Coding agents must infer behavior
- Output becomes non-deterministic
- Iteration safety breaks
- Validation becomes heuristic

The Spec Planner resolves this by making layer contents **explicit, inspectable, and constrained**.

---

## 4. Core Responsibilities

The Spec Planner is responsible for:

1. Translating intent semantics into concrete build instructions
2. Producing **layer-specific execution specs**
3. Enforcing architectural boundaries
4. Constraining LLM creativity via schemas and validators
5. Enabling selective regeneration during iteration

The Spec Planner is **not** responsible for:
- Writing implementation code
- Choosing technologies
- Modifying intent or architecture
- Performing orchestration

---

## 5. Design Philosophy: Intelligence with Guardrails

The Spec Planner follows a **hybrid design**:

- **LLM-based planning** for semantic flexibility
- **Deterministic validation** for correctness and stability

> **LLMs propose. Deterministic code validates.**

This allows the system to scale across many application types without hard-coding specs for each domain, while still guaranteeing correctness.

---

## 6. Inputs to the Spec Planner

Each spec planning invocation receives three inputs.

### 6.1 Intent (Read-only)

Semantic description of the application.

Example:
```json
{
  "primary_entities": {
    "Task": {
      "fields": {
        "title": { "type": "string", "required": true }
      }
    }
  },
  "operations": {
    "Task": ["create", "read", "update", "delete"]
  }
}
```

### 6.2 Architecture (Read-only)

Structural definition of layers and ordering.

Example:
```json
{
  "execution_layers": [
    { "id": "backend_services" },
    { "id": "backend_routes" }
  ]
}
```

### 6.3 Layer Context

Explicit context for the current layer.

Example:
```json
{
  "layer_id": "backend_services",
  "layer_role": "business_logic",
  "constraints": [
    "no_http",
    "no_ui",
    "must_call_database"
  ]
}
```

---

## 7. Outputs of the Spec Planner

The output is a **Layer Spec** — a structured JSON artifact describing exactly what must be built inside a layer.

Characteristics:
- Fully machine-readable
- Schema-bound
- Deterministic structure
- Independently validatable

Each architectural layer has its own spec schema.

---

## 8. Layer-Specific Specifications

### 8.1 Backend Models Spec

**Purpose**: Define domain data structures.

Example:
```json
{
  "models": [
    {
      "name": "Task",
      "type": "pydantic",
      "fields": [
        { "name": "title", "type": "str", "required": true }
      ]
    }
  ]
}
```

**Constraints**:
- No business logic
- No persistence logic
- No HTTP or UI concerns

---

### 8.2 Database Spec

**Purpose**: Define persistence schema and access primitives.

Example:
```json
{
  "tables": [
    {
      "entity": "Task",
      "columns": [
        { "name": "id", "type": "uuid", "primary_key": true },
        { "name": "title", "type": "string" }
      ]
    }
  ]
}
```

**Constraints**:
- No HTTP
- No UI
- No orchestration logic

---

### 8.3 Backend Services Spec

**Purpose**: Define business logic functions.

Example:
```json
{
  "services": [
    {
      "entity": "Task",
      "functions": [
        {
          "name": "create_task",
          "inputs": ["TaskCreate"],
          "returns": "Task"
        },
        {
          "name": "get_tasks",
          "inputs": [],
          "returns": "List[Task]"
        }
      ]
    }
  ]
}
```

**Constraints**:
- No HTTP
- No UI
- Must call database layer

---

### 8.4 Backend Routes Spec

**Purpose**: Define HTTP interface.

Example:
```json
{
  "routes": [
    {
      "method": "POST",
      "path": "/tasks",
      "service_call": "TaskService.create_task"
    }
  ]
}
```

**Constraints**:
- No business logic
- Must delegate to services

---

### 8.5 Backend App Bootstrap Spec

**Purpose**: Wire all backend components together.

Example:
```json
{
  "app_type": "fastapi",
  "routers": ["task_routes"],
  "middleware": []
}
```

**Constraints**:
- No domain logic
- No schema definitions

---

### 8.6 Frontend UI Spec

**Purpose**: Define UI composition and API usage.

Example:
```json
{
  "pages": [
    {
      "entity": "Task",
      "views": ["list", "create", "edit"],
      "api_endpoints": [
        { "method": "GET", "path": "/tasks" }
      ]
    }
  ]
}
```

**Constraints**:
- No business logic
- No persistence logic
- UI-only concerns

---

## 9. Validation Strategy

Each generated spec is validated deterministically.

Validation includes:
- JSON schema validation
- Forbidden concept detection
- Entity consistency checks
- Operation alignment with intent
- Architecture compliance

If validation fails:
- Spec is rejected
- Optionally regenerated
- Never silently corrected

---

## 10. Iteration and Change Handling

On user feedback or modification:

1. Intent is updated
2. Architecture is updated (if required)
3. Spec Planner regenerates **only affected layer specs**
4. Orchestrator triggers selective regeneration

This enables safe, incremental evolution.

---

## 11. Design Guarantees

The Spec Planner guarantees:

- Deterministic interfaces
- Flexible semantic planning
- Layer isolation
- Scalable support for diverse app types
- Inspectable and explainable execution plans

---

## 12. Key Design Principle

> **The Spec Planner is where intelligence is allowed — but only inside a cage built by schemas and validators.**

This principle ensures both scalability and correctness.

---

## 13. Summary

| Aspect | Decision |
|------|---------|
| Spec generation | LLM-based |
| Authority | Deterministic validators |
| Storage | Structured JSON |
| Scope | Per-layer |
| Responsibility | Define *what to build* |
| Role | Compiler-style planning |

