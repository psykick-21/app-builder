"""Orchestrator graph that coordinates intent interpreter and architect agents."""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..graph_states.orchestrator_state import OrchestratorState
from ..agents.intent_interpreter_agent import IntentInterpreterAgent
from ..agents.architect_agent import ArchitectAgent
from ..utils.system_config import system_config


# ==================== Save Nodes ====================

def save_intent_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Save intent to spec directory based on thread_id from config.
    
    Saves intent.json to generated_apps/<thread_id>/spec/intent.json
    """
    intent = state.get("intent")
    
    if not intent:
        # Nothing to save
        return state
    
    # Infer app_id (thread_id) from config
    if config is None:
        raise ValueError("config is required to get thread_id")
    
    # Access configurable from RunnableConfig (RunnableConfig is a TypedDict, supports dict access)
    configurable = config.get("configurable", {})  # type: ignore
    thread_id = configurable.get("thread_id") if isinstance(configurable, dict) else None
    if not thread_id:
        raise ValueError("thread_id is required in config.configurable to save intent")
    
    # Create directory structure: generated_apps/<thread_id>/spec/
    spec_dir = Path("generated_apps") / thread_id / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    file_path = spec_dir / "intent.json"
    
    # Save intent as JSON
    with open(file_path, "w") as f:
        json.dump(intent, f, indent=4)
    
    # Return state unchanged (no saved_files tracking)
    return state


def save_architecture_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Save architecture to spec directory based on thread_id from config.
    
    Saves architecture.json to generated_apps/<thread_id>/spec/architecture.json
    """
    architecture = state.get("architecture")
    
    if not architecture:
        # Nothing to save
        return state
    
    # Infer app_id (thread_id) from config
    if config is None:
        raise ValueError("config is required to get thread_id")
    
    # Access configurable from RunnableConfig (RunnableConfig is a TypedDict, supports dict access)
    configurable = config.get("configurable", {})  # type: ignore
    thread_id = configurable.get("thread_id") if isinstance(configurable, dict) else None
    if not thread_id:
        raise ValueError("thread_id is required in config.configurable to save architecture")
    
    # Create directory structure: generated_apps/<thread_id>/spec/
    spec_dir = Path("generated_apps") / thread_id / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    file_path = spec_dir / "architecture.json"
    
    # Save architecture as JSON
    with open(file_path, "w") as f:
        json.dump(architecture, f, indent=4, default=str)
    
    # Return state unchanged (no saved_files tracking)
    return state


# ==================== Graph Construction ====================

def create_orchestrator_graph():
    """Create and compile the orchestrator graph.
    
    Graph structure:
    intent_interpreter -> save_intent -> architect -> save_architecture -> END
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create checkpointer for state persistence
    checkpointer = MemorySaver()
    
    # Create the graph
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes - use agents directly with system config
    intent_config = system_config["intent_interpreter"]
    architect_config = system_config["architect"]
    
    workflow.add_node(
        "intent_interpreter",
        IntentInterpreterAgent(
            provider=intent_config["provider"],
            model=intent_config["model"],
            additional_kwargs=intent_config["additional_kwargs"],
        )
    )
    workflow.add_node("save_intent", save_intent_node)
    workflow.add_node(
        "architect",
        ArchitectAgent(
            provider=architect_config["provider"],
            model=architect_config["model"],
            additional_kwargs=architect_config["additional_kwargs"],
        )
    )
    workflow.add_node("save_architecture", save_architecture_node)
    
    # Set entry point
    workflow.set_entry_point("intent_interpreter")
    
    # Add edges - deterministic flow
    workflow.add_edge("intent_interpreter", "save_intent")
    workflow.add_edge("save_intent", "architect")
    workflow.add_edge("architect", "save_architecture")
    workflow.add_edge("save_architecture", END)
    
    # Compile the graph
    compiled = workflow.compile(checkpointer=checkpointer)
    
    return compiled


# ==================== Convenience Function ====================

def run_orchestrator(
    raw_user_input: str = None,
    user_feedback: str = None,
    agent_registry: list = None,
    existing_intent: dict = None,
    existing_architecture: dict = None,
    app_id: str = None,
):
    """Run the orchestrator graph with given inputs and yield events.
    
    Args:
        raw_user_input: User's application description (for CREATE mode)
        user_feedback: User feedback for modifying intent (for MODIFY mode)
        agent_registry: List of available generator agents
        existing_intent: Existing intent (for MODIFY mode)
        existing_architecture: Existing architecture (for ITERATIVE mode)
        app_id: Application identifier
        
    Yields:
        Dictionary with 'node' and 'state' keys for each event
    """
    # Load agent registry if not provided
    if agent_registry is None:
        registry_path = Path("src/ai/utils/agent_registry.json")
        if registry_path.exists():
            with open(registry_path, "r") as f:
                agent_registry = json.load(f)
        else:
            agent_registry = []
    
    # Generate UUID for thread_id if app_id not provided
    thread_id = app_id if app_id is not None else str(uuid.uuid4())
    
    # Create initial state
    initial_state: OrchestratorState = {
        "raw_user_input": raw_user_input,
        "user_feedback": user_feedback,
        "existing_intent": existing_intent,  # For MODIFY mode
        "agent_registry": agent_registry,
        "intent": existing_intent,  # Initial intent (will be updated by agent)
        "architecture": existing_architecture,
        "messages": [],
    }
    
    # Create runnable config with UUID thread_id
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    
    # Create and run the graph with streaming
    graph = create_orchestrator_graph()
    
    # Stream events and yield them
    for event in graph.stream(initial_state, config=config):
        # Each event is a dict with node names as keys
        for node_name, node_output in event.items():
            # Yield event information
            yield {
                "node": node_name,
                "state": node_output if isinstance(node_output, dict) else None,
            }
