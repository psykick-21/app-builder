# Code Generation Agents & Agent Repository — Detailed Specification

## 0. Scope of This Document

This document **only** defines:
- Code-generation agents (no semantic, planning, or orchestration agents)
- Their responsibilities, inputs, outputs, and filesystem ownership
- A static **Agent Repository (Registry)** limited to code agents

Non-code agents such as the Intent Interpreter, Architect, Orchestrator, and Validator are **explicitly out of scope** for this document.

This separation is intentional and aligns with the system’s architectural boundaries.

---

## 1. Design Principles for Code Agents

All code agents follow these strict principles:

1. **One agent per architectural responsibility**  
   Agents map to *change boundaries*, not convenience.

2. **Exclusive filesystem ownership**  
   Each agent owns a specific directory or file set.

3. **Deterministic regeneration**  
   Agents may overwrite files they own, but must not touch others.

4. **No cross-agent side effects**  
   Agents communicate only through explicit artifacts.

5. **Closed-world availability**  
   Only agents defined in the Agent Repository may be used.

---

## 2. Mandatory Code Agents (MVP-Core)

These agents are **required** to build a minimally correct full-stack application that supports iteration.

---

## 2.1 Backend Model Agent

**Agent ID**: `BackendModelAgent`

### Purpose
Translate domain entities from the intent into backend data models.

### Responsibilities
- Generate Python model classes
- Reflect entity fields accurately
- Update models when schema changes

### Inputs
```python
entities: dict
architecture_layer: dict
```

### Outputs
- Python model files

### Filesystem Ownership
```
backend/models/
```

### Constraints
- No business logic
- No API routing
- No database session logic

---

## 2.2 Backend Service Agent

**Agent ID**: `BackendServiceAgent`

### Purpose
Implement business logic and CRUD operations using models.

### Responsibilities
- Create, read, update, delete logic
- Encapsulate domain behavior

### Inputs
```python
entities: dict
architecture_layer: dict
```

### Outputs
- Service modules

### Filesystem Ownership
```
backend/services/
```

### Constraints
- No HTTP routing
- Must import models explicitly

---

## 2.3 Backend Route Agent

**Agent ID**: `BackendRouteAgent`

### Purpose
Expose backend functionality through HTTP APIs.

### Responsibilities
- Define FastAPI routes
- Map HTTP requests to service calls

### Inputs
```python
architecture_layer: dict
```

### Outputs
- Route files

### Filesystem Ownership
```
backend/routes/
```

### Constraints
- No business logic
- No model definitions

---

## 2.4 Backend Application Bootstrap Agent

**Agent ID**: `BackendAppBootstrapAgent`

### Purpose
Create and wire the backend application entrypoint.

### Responsibilities
- Initialize FastAPI app
- Register routers
- Define application startup logic

### Inputs
```python
architecture_layer: dict
available_routes: list[str]
```

### Outputs
- Application entry file (e.g., `main.py`)

### Filesystem Ownership
```
backend/main.py
```

### Constraints
- No business logic
- No schema definitions

---

## 2.5 Frontend UI Agent

**Agent ID**: `FrontendAgent`

### Purpose
Generate a simple UI for interacting with the backend.

### Responsibilities
- Render forms and lists
- Call backend APIs
- Handle basic user interaction

### Inputs
```python
intent: dict
backend_api_contract: dict
architecture_layer: dict
```

### Outputs
- Streamlit UI files

### Filesystem Ownership
```
frontend/
```

### Constraints
- UI logic only
- No backend logic

---

## 3. Bonus / Optional Code Agents (Not Required for MVP)

These agents are **not mandatory** for the core MVP, but are explicitly designed as **extension points**.

---

## 3.1 Database Setup & Persistence Agent (Bonus)

**Agent ID**: `DatabaseAgent`

### Purpose
Provide basic database persistence using SQLite.

### Responsibilities
- Initialize SQLite database
- Create tables from model definitions
- Manage basic DB connection setup

### Inputs
```python
entities: dict
database_config: dict
```

### Outputs
- Database initialization scripts
- Connection utilities

### Filesystem Ownership
```
backend/db/
```

### Constraints
- SQLite only
- No migration engine
- No production tuning

### Notes
This agent enables:
- Persistent storage
- More realistic application behavior

It is intentionally marked as **bonus** to avoid MVP complexity creep.

---

## 4. Code Agent Repository (Canonical Configuration)

### 4.1 Purpose

The **Code Agent Repository** is a static JSON configuration enumerating all available code-generation agents.

It is:
- Loaded at application startup
- Passed read-only to the Architect
- Enforced by the Orchestrator

If an agent is not listed here, it cannot be planned or executed.

---

### 4.2 Agent Repository JSON

```json
{
  "code_agents": [
    {
      "agent_id": "BackendModelAgent",
      "category": "code_generation",
      "layer_type": "backend_models",
      "description": "Generates backend data models from entities",
      "output_scope": "backend/models",
      "mandatory": true
    },
    {
      "agent_id": "BackendServiceAgent",
      "category": "code_generation",
      "layer_type": "backend_services",
      "description": "Implements business logic and CRUD operations",
      "output_scope": "backend/services",
      "mandatory": true
    },
    {
      "agent_id": "BackendRouteAgent",
      "category": "code_generation",
      "layer_type": "backend_routes",
      "description": "Exposes HTTP APIs using FastAPI",
      "output_scope": "backend/routes",
      "mandatory": true
    },
    {
      "agent_id": "BackendAppBootstrapAgent",
      "category": "code_generation",
      "layer_type": "backend_app",
      "description": "Bootstraps the backend application entrypoint",
      "output_scope": "backend/main.py",
      "mandatory": true
    },
    {
      "agent_id": "FrontendAgent",
      "category": "code_generation",
      "layer_type": "frontend_ui",
      "description": "Generates Streamlit-based frontend UI",
      "output_scope": "frontend",
      "mandatory": true
    },
    {
      "agent_id": "DatabaseAgent",
      "category": "code_generation",
      "layer_type": "database",
      "description": "Initializes SQLite database and tables",
      "output_scope": "backend/db",
      "mandatory": false
    }
  ]
}
```

---

## 5. Why This Agent Set Is Correct

This set of code agents is:
- Minimal but complete
- Architecturally clean
- Iteration-safe
- Extendable without refactoring

It cleanly separates:
- Schema
- Business logic
- API surface
- Application wiring
- UI
- Persistence (optional)

---

## 6. Summary

The system defines a closed set of code-generation agents, each owning a distinct architectural responsibility and filesystem scope. A static Agent Repository enumerates these agents and is used by the Architect to plan execution and by the Orchestrator to enforce correctness. This design enables deterministic generation, selective regeneration during iteration, and controlled extensibility while keeping the MVP scope achievable within strict time constraints.

