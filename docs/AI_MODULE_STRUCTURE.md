## AI Module Structure

### Directory Layout

```
src/ai/
├── agents/         # Agent classes with LLM logic
├── graphs/         # LangGraph workflow definitions
├── graph_states/   # TypedDict state schemas for graphs
├── prompts/        # System and user prompts
├── models/         # Pydantic models for tools and responses
└── utils/          # Utility functions (HTML parsing, etc.)
```

---

### 1. **agents/** - Agent Classes

**Pattern**: Each agent is a class with `__init__`, `execute()`, and `__call__()` methods.

**Structure**:
```python
class AgentName:
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        # Initialize LLM
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        # Optionally bind tools
        self.llm_with_tools = self.llm.bind_tools(tools, tool_choice="required")
        # Create chain with prompt
        self.chain = PROMPT | self.llm_with_tools

    @traceable(name="agent_name.llm_call")
    def execute(self, state: dict):
        # Core LLM invocation logic
        # Extract inputs from state
        # Call self.chain.invoke(inputs)
        # Return LLM response

    def __call__(self, state: dict) -> dict:
        # Node execution wrapper for LangGraph
        # Extract tracking metadata from state
        # Track inputs using track_node context manager
        # Call self.execute(state)
        # Track outputs using track_node_execution
        # Return updated state
```

**Key Points**:
- `__init__`: Setup LLM, tools, and chain
- `execute()`: Core LLM call decorated with `@traceable`
- `__call__()`: LangGraph node interface with tracking

---

### 2. **graphs/** - LangGraph Workflows

**Pattern**: Define nodes, routing logic, and compile workflow with checkpointer.

**Structure**:
```python
# Node functions
def node_name(state: StateClass) -> StateClass:
    # Process state
    # Call agent or perform logic
    return updated_state

# Router functions
def route_after_node(state: StateClass) -> Literal["option1", "option2", "end"]:
    # Decision logic based on state
    return "option1"  # or "option2" or "end"

# Workflow factory
def create_workflow():
    checkpointer = MemorySaver()
    workflow = StateGraph(StateClass)
    
    # Add nodes
    workflow.add_node("node_name", node_name)
    workflow.add_node("other_node", other_node)
    
    # Set entry point
    workflow.set_entry_point("node_name")
    
    # Add edges (conditional or direct)
    workflow.add_conditional_edges(
        "node_name",
        route_after_node,
        {"option1": "other_node", "option2": "end"}
    )
    workflow.add_edge("other_node", END)
    
    # Compile and wrap with tracking
    compiled = workflow.compile(checkpointer=checkpointer)
    
    # Wrap invoke/stream with workflow-level tracking
    original_invoke = compiled.invoke
    def tracked_invoke(inputs, config=None):
        tracking_metadata = inputs.get("_tracking_metadata", {})
        if config is None:
            config = {}
        config["run_name"] = "workflow_name"
        with track_workflow("workflow_name", metadata=tracking_metadata):
            return original_invoke(inputs, config)
    
    compiled.invoke = tracked_invoke
    return compiled
```

**Key Points**:
- Node functions: Process state, call agents
- Router functions: Conditional branching logic
- Workflow factory: StateGraph setup with checkpointer
- Tracking wrappers: Add monitoring to invoke/stream

---

### 3. **graph_states/** - State Schemas

**Pattern**: TypedDict with annotated fields for LangGraph state.

**Structure**:
```python
from typing import Optional
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage
import operator

class WorkflowState(TypedDict, total=False):
    # Messages list (LangGraph standard)
    messages: Annotated[list[AnyMessage], operator.add]
    
    # Input fields
    input_field: str
    input_list: list[dict]
    
    # Output/intermediate fields
    result: Optional[dict]
    intermediate_result: Optional[dict]
    
    # Tracking metadata (standard across all workflows)
    _tracking_metadata: Optional[dict]
    
    # Config for checkpointing
    _config: Optional[dict]
```

**Key Points**:
- Use `TypedDict` with `total=False`
- `messages` field with `operator.add` annotation for LangGraph
- Separate input, output, and metadata fields
- `_tracking_metadata` for LangSmith tracking
- `_config` for checkpoint/thread management

---

### 4. **prompts/** - Prompt Templates

**Pattern**: Define static system prompts and compose with ChatPromptTemplate.

**Structure**:
```python
from langchain_core.prompts import (
    ChatPromptTemplate, 
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)

# Static system prompt (no template variables)
AGENT_SYSTEM_PROMPT = """## ROLE
You are an agent that...

## GUIDELINES
- Guideline 1
- Guideline 2
"""

# Full prompt with placeholders
AGENT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(AGENT_SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(
        """Context:\n{context_field}\n\nInput:\n{input_field}"""
    ),
    MessagesPlaceholder(variable_name="messages"),  # For conversation history
])
```

**Key Points**:
- Static system prompt as module constant
- Compose with `ChatPromptTemplate.from_messages()`
- Use `MessagesPlaceholder` for conversation history
- Keep prompts separate from agent logic

---

### 5. **models/** - Pydantic Models

**Pattern**: Define tool schemas and response models using Pydantic.

**Structure**:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

# Tool schemas (for structured tool calling)
class ToolNameTool(BaseModel):
    """Tool description."""
    
    field1: str = Field(description="Field description")
    field2: Optional[str] = Field(default=None, description="Optional field")
    field3: List[str] = Field(description="List field")

# Response models (for structured outputs)
class AgentResponse(BaseModel):
    intent: Literal["CREATE", "UPDATE", None]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    tool_to_execute: Optional[ToolNameTool]
```

**Key Points**:
- Use `BaseModel` for all models
- Add detailed `Field` descriptions (used by LLM)
- Use `Optional` for optional fields with defaults
- Use `Literal` for enum-like fields
- Validation constraints: `ge`, `le` for numeric bounds

---

### 6. **utils/** - Utility Functions

**Pattern**: Pure functions for data transformation.

**Structure**:
```python
def parse_data(input_data: Dict) -> Dict:
    """Transform input data to expected format."""
    # Parsing logic
    return transformed_data

def extract_field(data: Dict, field: str) -> str:
    """Extract specific field from nested data."""
    # Extraction logic
    return field_value
```

**Key Points**:
- Pure functions, no side effects
- Type hints for all parameters and returns
- Docstrings with clear descriptions
- Common utils: HTML parsing, date formatting, data extraction

---

### Tool Creation Pattern

When agents use tools, create them with `StructuredTool.from_function`:

```python
def create_agent_tools():
    tool = StructuredTool.from_function(
        func=lambda **kwargs: kwargs,  # Return args as-is
        name="tool_name",
        description="When to use this tool",
        args_schema=ToolNameTool,  # Pydantic model
    )
    return [tool]
```

---

### Tracking Pattern

All agents use standardized tracking:

```python
# In agent.__call__()
tracking_metadata = state.get("_tracking_metadata", {})

# Track node execution
with track_node(
    node_name="node_name",
    workflow_name="workflow_name", 
    inputs=node_inputs,
    metadata=tracking_metadata
):
    result = self.execute(state)

# Track outputs
track_node_execution(
    node_name="node_name",
    workflow_name="workflow_name",
    inputs=node_inputs,
    outputs=node_outputs,
    metadata=tracking_metadata
)
```

---

### Naming Conventions

- **Agents**: `{Purpose}Agent` (e.g., `ActionAgent`, `BillerAgent`)
- **Graphs**: `{purpose}_graph.py` with `create_{purpose}_workflow()` function
- **States**: `{Purpose}State` (e.g., `ActionAgentState`)
- **Prompts**: `{AGENT}_SYSTEM_PROMPT` and `{AGENT}_PROMPT` constants
- **Tools**: `{Action}Tool` (e.g., `EmailDraftTool`, `GatherContextTool`)