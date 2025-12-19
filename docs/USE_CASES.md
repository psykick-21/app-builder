## Use Case 1 — Clear, Well-Scoped CRUD (Baseline Sanity Test)

**User prompt**

> “Build a simple task management app.
> I should be able to create, view, update, and delete tasks.
> Each task should have a title and a description.
> Keep the UI very basic.”

**Why this is important**

* Establishes the **happy path**
* Tests full MVP flow with:

  * One primary entity
  * Standard CRUD operations
  * Default UI expectations
* Ideal for validating determinism and baseline correctness

**What this will test**

* Intent extraction accuracy
* Stable architecture planning
* Full execution queue
* End-to-end generation without iteration

---

## Use Case 2 — Vague, Under-Specified Prompt (Ambiguity Handling)

**User prompt**

> “I want a small app to track things I need to do daily.”

**Why this is important**

* Simulates **real user ambiguity**
* Forces the Intent Interpreter to:

  * Infer *minimal viable semantics*
  * Record assumptions explicitly instead of inventing features
* Tests restraint and schema discipline

**What this will test**

* Assumption capture in `intent.json`
* Avoidance of over-engineering
* Whether the system stays minimal and safe

---

## Use Case 3 — Slightly Complex Domain with Constraints

**User prompt**

> “Create an expense tracking app.
> Each expense should have an amount, category, date, and optional notes.
> I only need this for myself, no login or multi-user support.”

**Why this is important**

* Introduces:

  * Mixed field types (number, string, date, optional)
  * Explicit non-goals
* Still within MVP scope but more realistic

**What this will test**

* Type handling in intent schema
* Correct model generation
* Respecting explicit constraints (e.g., single-user)
* Frontend form generation with optional fields

---

## Use Case 4 — Opinionated Workflow-Oriented Prompt (Non-Trivial Semantics)

**User prompt**

> “Build a lightweight bug tracker for my personal projects.
> Each bug should have a title, severity, status, and description.
> I want to see all open bugs first.”

**Why this is important**

* Introduces **semantic intent** beyond pure CRUD:

  * Status fields
  * Implied ordering / prioritization
* Still achievable without custom logic explosions

**What this will test**

* How much semantic meaning is captured vs deferred
* Whether the system avoids hardcoding behavior not explicitly requested
* Clean separation between intent vs implementation

---

## Use Case 5 — Iteration-Heavy Prompt (Critical for Evaluation)

**Initial user prompt**

> “Build a notes app where I can create, edit, and delete notes.
> Each note should have a title and content.”

**Follow-up feedback (after generation)**

> “Add tags to notes, and I want to filter notes by tag.”

**Why this is important**

* This is the **most important test case**
* Directly exercises:

  * MODIFY mode of Intent Interpreter
  * Architecture preservation
  * Impact analysis
  * Selective regeneration

**What this will test**

* Stability of `architecture.json`
* Correct identification of affected layers
* No unnecessary regeneration
* End-to-end iteration safety

---

## Why These 5 Together Are Sufficient

Taken together, these prompts cover:

* ✅ Clear vs vague intent
* ✅ Simple vs moderately complex schemas
* ✅ Explicit constraints and non-goals
* ✅ Semantic nuance without overreach
* ✅ **At least one full feedback-driven regeneration cycle (mandatory for MVP)**

If the system handles these five correctly, it strongly validates the **core thesis of the project**:
controlled, deterministic, agentic software evolution 