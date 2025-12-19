# Lyzr Agentic App Builder — Project Overview & System Design

## 1. Project Overview

### 1.1 What Are We Building?

We are building an **Agentic App Builder** — a system that converts **natural language application descriptions** into **working, runnable full-stack applications**, and then **iteratively evolves them** based on user feedback.

The system is **agentic**, not because it uses many LLMs, but because it:
- Separates reasoning from execution
- Maintains explicit state and artifacts
- Uses deterministic orchestration
- Supports controlled iteration instead of full regeneration

> The goal is not code generation alone, but **controlled software evolution**.

---

### 1.2 Problem We Are Solving

Most AI app builders:
- Generate code in a single pass
- Lose context after generation
- Break down when users request changes

This project directly addresses those limitations by:
- Introducing a **structured intent layer**
- Planning a **stable execution architecture**
- Orchestrating agents with **explicit control flow**
- Treating user feedback as **first-class input**, not an afterthought

---

## 2. Core Design Philosophy

The system is built around three non-negotiable principles:

### 2.1 Separation of Concerns

Each responsibility is isolated:
- Understanding intent
- Planning structure
- Generating code
- Validating output
- Orchestrating execution

No component is allowed to overstep its boundary.

---

### 2.2 Determinism Over Creativity

LLMs are used only where **semantic reasoning** is required.

Everything else — validation, orchestration, retries, file handling — is:
- Deterministic
- Inspectable
- Reproducible

---

### 2.3 Iteration as a First-Class Feature

User feedback is not handled by patching code.

Instead:
- Feedback evolves intent
- Intent re-drives planning
- Orchestration selectively regenerates only what is affected

This enables **safe and explainable iteration**.

---

## 3. High-Level System Architecture

The system is composed of five major subsystems:

1. **Intent Interpretation** — converts language into structured meaning
2. **Architectural Planning** — defines execution layers and dependencies
3. **Code Generation** — produces backend and frontend code
4. **Validation** — enforces quality gates deterministically
5. **Orchestration** — coordinates everything end-to-end

All subsystems are wired together using **LangGraph**.

---

## 4. Key Components

### 4.1 Intent Interpreter

**Purpose**
- Translate natural language into a structured intent specification
- Evolve intent based on user feedback

**Key Characteristics**
- Single-writer of intent artifacts
- Schema-enforced via Pydantic
- Operates in CREATE and MODIFY modes

**Output**
- `intent.json`

---

### 4.2 Architect (Planner)

**Purpose**
- Convert intent into a stable execution architecture

**Key Characteristics**
- Stateless
- Uses a closed-world agent registry
- Preserves architectural identifiers across iterations

**Output**
- `architecture.json`

---

### 4.3 Code Generation Agents

**Purpose**
- Generate application code in well-defined layers

**Mandatory Code Agents**
- Backend Model Agent
- Backend Service Agent
- Backend Route Agent
- Backend App Bootstrap Agent
- Frontend UI Agent

**Optional / Bonus**
- Database (SQLite) Agent

Each agent owns a strict filesystem scope and can be selectively re-executed.

---

### 4.4 Code Validation Agent

**Purpose**
- Enforce quality gates after each generation step

**Characteristics**
- Non-LLM
- Deterministic
- Layer-aware

**Checks Performed**
- Syntax validation
- Import resolution
- Layer constraint enforcement
- Best-effort runtime checks

---

### 4.5 Orchestrator

**Purpose**
- Act as the control plane for the entire system

**Responsibilities**
- Maintain global state
- Invoke agents in correct order
- Persist artifacts
- Run validation and retry loops
- Handle feedback-driven iteration

**Implementation**
- Implemented as a LangGraph workflow
- Uses deterministic routing and retry logic

---

## 5. Artifact-Driven Execution Model

The system treats the filesystem as the **source of truth**.

Each application instance contains:

```
/spec
  ├── intent.json
  ├── architecture.json
  ├── code_map.json
  └── changes.log
/backend
/frontend
```

Artifacts enable:
- Inspectability
- Diffing
- Safe iteration
- Partial regeneration

---

## 6. End-to-End Flow (Initial Generation)

1. User provides app description
2. Intent Interpreter generates `intent.json`
3. Architect generates `architecture.json`
4. Orchestrator builds execution queue
5. Code agents generate code layer by layer
6. Validation agent gates each layer
7. Runnable app is produced

---

## 7. Feedback & Iteration Flow

1. User provides feedback
2. Intent is evolved (MODIFY mode)
3. Architect re-plans with existing architecture
4. Orchestrator performs impact analysis
5. Only affected layers are regenerated
6. Validation runs on regenerated scope only

This avoids full rebuilds and preserves stability.

---

## 8. Why LangChain + LangGraph

- **LangChain** provides structured LLM interaction
- **LangGraph** provides explicit control flow, retries, and branching

This combination allows:
- True agentic workflows
- Clear separation between reasoning and control
- Visualizable execution graphs

---

## 9. What This Project Demonstrates

This project demonstrates:
- Agentic system design beyond prompt chaining
- Deterministic orchestration with LLM components
- Realistic handling of user-driven iteration
- Production-aligned architectural thinking

It intentionally prioritizes **clarity and control** over surface-level polish.

---

## 10. Conclusion

The Lyzr Agentic App Builder is a deliberately designed system that showcases how LLM-powered agents can be composed into a predictable, inspectable, and extensible software-building workflow. By combining structured intent, stable planning, layered code generation, deterministic validation, and explicit orchestration, the project demonstrates a practical approach to building agentic systems that can evolve safely over time.

> This is not a chatbot that writes code — it is a system that **builds and evolves software**.

