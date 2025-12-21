"""Code agents graph - placeholder for future implementation."""

import uuid
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from ..graph_states.code_agents_state import CodeAgentsState
from ..agents.code_agents.backend_model_agent import BackendModelAgent
from ..agents.code_agents.backend_service_agent import BackendServiceAgent
from ..utils.system_config import system_config


def initialize_execution_queue(state: CodeAgentsState, config: Optional[RunnableConfig] = None) -> CodeAgentsState:
    """Initialize the execution queue based on the architecture plan."""
    architecture = state.get("architecture")

    if not architecture:
        raise ValueError("architecture is required in state")
    
    # Layer IDs that have implemented agents
    implemented_layers = ["backend_models"]

    execution_queue = [(layer["id"], layer["path"]) for layer in architecture["execution_layers"] if layer["id"] in implemented_layers]
    return {
        **state,
        "execution_queue": execution_queue,
        "next_layer_index": 0,
    }


def global_router(state: CodeAgentsState, config: Optional[RunnableConfig] = None):
    """Global router to determine the next layer to execute."""
    next_layer_index = state.get("next_layer_index")
    execution_queue = state.get("execution_queue")
    if next_layer_index == len(execution_queue):
        return END
    
    next_node = execution_queue[next_layer_index][0]

    if next_node == "backend_models":
        return "backend_model_agent"
    elif next_node == "backend_services":
        return "backend_service_agent"
    elif next_node == "backend_routes":
        return "backend_route_agent"
    elif next_node == "frontend_ui":
        return "frontend_agent"
    elif next_node == "database":
        return "database_agent"
    elif next_node == "backend_app":
        return "backend_app_agent"
    else:
        raise ValueError(f"Unknown layer: {next_node}")



def create_code_agents_graph():
    """Create and compile the code agents graph.
    
    Graph structure:
    initialize_execution_queue -> backend_model_agent -> backend_service_agent -> backend_route_agent -> frontend_agent -> END
    """

    # Create checkpointer for state persistence
    checkpointer = MemorySaver()

    # Create the graph
    workflow = StateGraph(CodeAgentsState)
    
    # Add nodes
    workflow.add_node("initialize_execution_queue", initialize_execution_queue)
    workflow.add_node("backend_model_agent", BackendModelAgent(
        provider=system_config["backend_model_agent"]["provider"],
        model=system_config["backend_model_agent"]["model"],
        additional_kwargs=system_config["backend_model_agent"]["additional_kwargs"],
    ))
    
    # Add edges
    workflow.set_entry_point("initialize_execution_queue")

    workflow.add_conditional_edges("initialize_execution_queue", global_router)
    workflow.add_conditional_edges("backend_model_agent", global_router)
    # workflow.add_conditional_edges("backend_service_agent", global_router)
    # workflow.add_conditional_edges("backend_route_agent", global_router)
    # workflow.add_conditional_edges("frontend_agent", global_router)
    # workflow.add_conditional_edges("database_agent", global_router)
    # workflow.add_conditional_edges("backend_app_agent", global_router)
    # workflow.add_edge("END", END)
    
    # Compile the graph
    compiled = workflow.compile(checkpointer=checkpointer)
    
    return compiled


# ==================== Convenience Function ====================

def run_code_agents(
    intent: Dict[str, Any] = None,
    architecture: Dict[str, Any] = None,
    specs: list = None,
    app_id: str = None,
):
    """Run the code agents graph with given inputs and yield events.
    
    Args:
        intent: Intent specification dictionary
        architecture: Architecture plan dictionary
        specs: List of spec dictionaries for each layer
        app_id: Application identifier (used as thread_id)
        
    Yields:
        Dictionary with 'node' and 'state' keys for each event
    """
    if not intent:
        raise ValueError("intent is required")
    if not architecture:
        raise ValueError("architecture is required")
    
    # Generate UUID for thread_id if app_id not provided
    thread_id = app_id if app_id is not None else str(uuid.uuid4())
    
    # Create initial state
    initial_state: CodeAgentsState = {
        "intent": intent,
        "architecture": architecture,
        "specs": specs or [],
        "manifests": [],
        "execution_queue": None,
        "next_layer_index": None,
    }
    
    # Create runnable config with UUID thread_id
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    
    # Create and run the graph with streaming
    graph = create_code_agents_graph()
    
    # Stream events and yield them
    for event in graph.stream(initial_state, config=config):
        # Each event is a dict with node names as keys
        for node_name, node_output in event.items():
            # Yield event information
            yield {
                "node": node_name,
                "state": node_output if isinstance(node_output, dict) else None,
            }
