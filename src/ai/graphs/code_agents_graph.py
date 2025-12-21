"""Code agents graph - placeholder for future implementation."""

import uuid
import os
import stat
from typing import Dict, Any, Optional
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from ..graph_states.code_agents_state import CodeAgentsState
from ..agents.code_agents.backend_model_agent import BackendModelAgent
from ..agents.code_agents.backend_service_agent import BackendServiceAgent
from ..agents.code_agents.database_agent import DatabaseAgent
from ..agents.code_agents.backend_router_agent import BackendRouterAgent
from ..agents.code_agents.backend_app_agent import BackendAppAgent
from ..agents.code_agents.frontend_agent import FrontendAgent
from ..utils.system_config import system_config


def initialize_execution_queue(state: CodeAgentsState, config: Optional[RunnableConfig] = None) -> CodeAgentsState:
    """Initialize the execution queue based on the architecture plan."""
    architecture = state.get("architecture")

    if not architecture:
        raise ValueError("architecture is required in state")
    
    # Layer IDs that have implemented agents
    implemented_layers = ["backend_models", "database", "backend_services", "backend_routes", "backend_app", "frontend_ui"]

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
        return "finalize"
    
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


def finalize(state: CodeAgentsState, config: Optional[RunnableConfig] = None) -> CodeAgentsState:
    """Finalize the code generation by creating helper files.
    
    Creates:
    - requirements.txt: Python dependencies
    - run.sh: Startup script
    """
    root_dir = state.get("root_dir")
    if not root_dir:
        raise ValueError("root_dir is required in state")
    
    manifests = state.get("manifests", [])
    
    # Collect all unique dependencies from all manifests
    all_dependencies = set()
    
    # Cycle through each manifest
    for manifest in manifests:
        # Get manifest_files for this layer
        manifest_files = manifest.get("manifest_files", [])
        
        # For each file in the manifest
        for manifest_file in manifest_files:
            # Get dependencies for this file
            dependencies = manifest_file.get("dependencies", [])
            
            # Add each dependency to the set (automatically handles uniqueness)
            for dep in dependencies:
                if dep:  # Only add non-empty dependencies
                    all_dependencies.add(dep.strip())
    
    # Sort dependencies alphabetically for consistent output
    sorted_dependencies = sorted(all_dependencies)
    
    # Create requirements.txt-like text
    # Format: one dependency per line
    requirements_text = "\n".join(sorted_dependencies)

    with open(root_dir / "requirements.txt", "w") as f:
        f.write(requirements_text)

    # Create run.sh
    run_sh_content = """#!/bin/bash

# Generated App - Startup Script
# This script sets up and runs both backend and frontend

set -e  # Exit on error

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo "🚀 Starting App Setup..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Check Python
echo ""
echo "📋 Step 1/4: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Step 2: Install dependencies
echo ""
echo "📦 Step 2/4: Installing dependencies..."
if command -v uv &> /dev/null; then
    echo "Using uv for faster installation..."
    uv pip install -r requirements.txt
else
    echo "Using pip..."
    pip3 install -r requirements.txt
fi
echo "✅ Dependencies installed"

# Step 3: Initialize database
echo ""
echo "🗄️  Step 3/4: Initializing database..."
PYTHONPATH="$APP_DIR:$PYTHONPATH" python3 -c "from backend.db.init_db import init_database; init_database(); print('✅ Database initialized')"

# Step 4: Start services
echo ""
echo "🚀 Step 4/4: Starting services..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Starting Backend API on http://localhost:1234"
echo "Starting Frontend UI on http://localhost:4321"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
PYTHONPATH="$APP_DIR:$PYTHONPATH" python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 1234 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
sleep 3  # Give backend time to start

# Check if backend is actually running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start. Check backend.log for details:"
    tail -n 20 backend.log
    exit 1
fi

# Start frontend
PYTHONPATH="$APP_DIR:$PYTHONPATH" streamlit run frontend/app.py > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
sleep 3  # Give frontend time to start

# Check if frontend is actually running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend failed to start. Check frontend.log for details:"
    tail -n 20 frontend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 App is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Backend API:  http://localhost:1234"
echo "📍 API Docs:     http://localhost:1234/docs"
echo "📍 Frontend UI:  http://localhost:4321"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
"""
    
    run_sh_path = root_dir / "run.sh"
    with open(run_sh_path, "w") as f:
        f.write(run_sh_content)
    
    # Make run.sh executable
    import os
    import stat
    os.chmod(run_sh_path, os.stat(run_sh_path).st_mode | stat.S_IEXEC)

    return state


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
    workflow.add_node("database_agent", DatabaseAgent(
        provider=system_config["database_agent"]["provider"],
        model=system_config["database_agent"]["model"],
        additional_kwargs=system_config["database_agent"]["additional_kwargs"],
    ))
    workflow.add_node("backend_service_agent", BackendServiceAgent(
        provider=system_config["backend_service_agent"]["provider"],
        model=system_config["backend_service_agent"]["model"],
        additional_kwargs=system_config["backend_service_agent"]["additional_kwargs"],
    ))
    workflow.add_node("backend_route_agent", BackendRouterAgent(
        provider=system_config["backend_router_agent"]["provider"],
        model=system_config["backend_router_agent"]["model"],
        additional_kwargs=system_config["backend_router_agent"]["additional_kwargs"],
    ))
    workflow.add_node("backend_app_agent", BackendAppAgent(
        provider=system_config["backend_app_agent"]["provider"],
        model=system_config["backend_app_agent"]["model"],
        additional_kwargs=system_config["backend_app_agent"]["additional_kwargs"],
    ))
    workflow.add_node("frontend_agent", FrontendAgent(
        provider=system_config["frontend_agent"]["provider"],
        model=system_config["frontend_agent"]["model"],
        additional_kwargs=system_config["frontend_agent"]["additional_kwargs"],
    ))
    workflow.add_node("finalize", finalize)
    
    # Add edges
    workflow.set_entry_point("initialize_execution_queue")

    workflow.add_conditional_edges("initialize_execution_queue", global_router)
    workflow.add_conditional_edges("backend_model_agent", global_router)
    workflow.add_conditional_edges("database_agent", global_router)
    workflow.add_conditional_edges("backend_service_agent", global_router)
    workflow.add_conditional_edges("backend_route_agent", global_router)
    workflow.add_conditional_edges("backend_app_agent", global_router)
    workflow.add_conditional_edges("frontend_agent", global_router)
    workflow.add_edge("finalize", END)
    
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
