# MVP & Bonus Features — Scope Definition

## 1. Purpose of This Document

This document clearly defines:
- **What is included in the MVP (Must-Have)**
- **What is intentionally deferred as Bonus (Nice-to-Have)**

The goal is to demonstrate **strong prioritization under time constraints**, while leaving a clean and credible extension path.

This scope is derived from the complete system design (Intent Interpreter, Architect, Code Agents, Validation, Orchestrator) and reflects what can be realistically delivered within a **3-day assignment window**.

---

## 2. Definition of MVP

The MVP is considered complete if the system can:

1. Take a natural language app description
2. Generate a runnable full-stack application
3. Validate generated code deterministically
4. Accept user feedback
5. Selectively regenerate affected parts of the application

Everything else is secondary.

---

## 3. MVP Features (Mandatory)

### 3.1 Natural Language → Structured Intent

**What is included**
- Single Intent Interpreter agent
- CREATE and MODIFY modes
- Schema-enforced intent generation via Pydantic
- Intent persistence as `intent.json`

**Why this is MVP-critical**
- Intent is the foundation of the entire system
- Enables deterministic downstream planning

---

### 3.2 Stable Architectural Planning

**What is included**
- Architect (Planner) agent
- Generation of `architecture.json`
- Stable execution layers with immutable IDs
- Closed-world agent selection via Agent Repository

**Why this is MVP-critical**
- Enables predictable orchestration
- Prevents LLM-driven architectural drift

---

### 3.3 Layered Code Generation

**What is included**

Mandatory code-generation agents:
- Backend Model Agent
- Backend Service Agent
- Backend Route Agent
- Backend Application Bootstrap Agent
- Frontend UI Agent

Each agent:
- Owns a strict filesystem scope
- Can be independently regenerated

**Why this is MVP-critical**
- Produces a complete, runnable application
- Supports selective regeneration

---

### 3.4 Deterministic Code Validation

**What is included**
- Single shared Code Validation Agent
- Syntax validation (AST-based)
- Import resolution checks
- Layer constraint enforcement

**Why this is MVP-critical**
- Prevents silent failures
- Enables controlled retry loops

---

### 3.5 Orchestrated Execution with LangGraph

**What is included**
- Central Orchestrator implemented as LangGraph
- Explicit state management
- Layer-by-layer execution
- Validation + retry loops

**Why this is MVP-critical**
- This is the core differentiator of the project
- Demonstrates true agentic control

---

### 3.6 Artifact-Driven Execution

**What is included**
- Filesystem as source of truth
- Persisted artifacts:
  - `intent.json`
  - `architecture.json`
  - `code_map.json`
  - `changes.log`

**Why this is MVP-critical**
- Enables inspectability and iteration
- Makes execution explainable

---

### 3.7 Feedback-Driven Iteration (One Complete Cycle)

**What is included**
- User provides feedback (e.g., add a field)
- Intent evolves (MODIFY mode)
- Architect re-plans with existing architecture
- Orchestrator performs impact analysis
- Only affected layers are regenerated

**Why this is MVP-critical**
- Explicitly required by the problem statement
- Demonstrates stateful evolution

---

## 4. MVP Non-Goals (Explicitly Excluded)

The following are intentionally **out of scope for MVP**:

- Authentication / multi-user support
- Production-grade UI
- Advanced database migrations
- Test generation
- Deployment pipelines
- Performance optimization

These exclusions demonstrate disciplined scoping.

---

## 5. Bonus Features (If Time Permits)

Bonus features are **not required**, but significantly strengthen the submission if partially implemented or even just designed.

---

### 5.1 Database & Persistence (SQLite)

**What can be added**
- Database Agent
- SQLite-based persistence
- Table creation from models

**Why this is a bonus**
- Adds realism
- Not required to demonstrate orchestration

---

### 5.2 LangSmith Observability

**What can be added**
- Trace agent calls
- Inspect LangGraph execution

**Why this is a bonus**
- Improves debuggability
- Shows production awareness

---

### 5.3 Improved Impact Analysis

**What can be added**
- More granular file-level regeneration
- Entity-to-file mapping

**Why this is a bonus**
- Improves efficiency
- Not required for correctness

---

### 5.4 Additional Code Agents

**What can be added**
- Database Migration Agent
- Test Generation Agent
- Documentation Agent

**Why this is a bonus**
- Demonstrates extensibility
- Not required for core flow

---

### 5.5 Runtime Execution from UI

**What can be added**
- One-click run from Streamlit
- Display server logs

**Why this is a bonus**
- Improves UX
- Not essential to orchestration

---

## 6. Success Criteria

The project is considered successful if:

- MVP features are fully functional
- At least one feedback-driven iteration works end-to-end
- Orchestration logic is explicit and inspectable
- The system can be understood in under 10 minutes by a reviewer

Bonus features enhance, but do not define, success.

---

## 7. Final Positioning Statement

> The MVP focuses on **control, determinism, and iteration**, not polish.

By clearly separating MVP and bonus features, the project demonstrates strong engineering judgment, realistic scoping, and a production-oriented mindset — exactly what is expected for an agentic systems assignment.

