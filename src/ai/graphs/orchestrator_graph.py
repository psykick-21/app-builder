"""Orchestrator graph that coordinates intent interpreter and architect agents."""
 
import json
import uuid
import copy
import os
import stat
from pathlib import Path
from typing import Dict, Any, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

from ..graph_states.orchestrator_state import OrchestratorState
from ..graph_states.code_agents_state import CodeAgentsState
from ..agents.intent_interpreter_agent import IntentInterpreterAgent
from ..agents.architect_agent import ArchitectAgent
from ..agents.spec_planner_agent import SpecPlannerAgent
from .code_agents_graph import create_code_agents_graph
from ..utils.system_config import system_config


def initialize_graph(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    configurable = config.get("configurable", {})  # type: ignore
    thread_id = configurable.get("thread_id") if isinstance(configurable, dict) else None
    if not thread_id:
        raise ValueError("thread_id is required in config.configurable to initialize graph")
    
    # Create directory structure: generated_apps/<thread_id>/spec/
    root_dir = Path("generated_apps") / thread_id
    root_dir.mkdir(parents=True, exist_ok=True)

    # Determine mode based on user_feedback
    if state.get("user_feedback"):
        mode = "MODIFY"
    else:
        mode = "CREATE"
    
    # existing_intent and existing_architecture should always come from state (checkpoint)
    # They are set by the finalize node after code generation completes
    
    # Load agent registry if not already in state
    agent_registry = state.get("agent_registry")
    if agent_registry is None:
        registry_path = Path("src/ai/utils/agent_registry.json")
        if registry_path.exists():
            with open(registry_path, "r") as f:
                agent_registry = json.load(f)
        else:
            agent_registry = []
    
    # Load layer constraints if not already in state
    layer_constraints = state.get("layer_constraints")
    if layer_constraints is None:
        layer_constraints_path = Path("src/ai/utils/layer_constraints.json")
        layer_constraints = {}
        if layer_constraints_path.exists():
            with open(layer_constraints_path, "r") as f:
                layer_constraints = json.load(f)
    
    return {
        **state,
        "root_dir": root_dir,
        "mode": mode,
        "agent_registry": agent_registry,
        "layer_constraints": layer_constraints,
    }
    


# ==================== Save Nodes ====================

def save_intent_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Save intent to spec directory using root_dir from state.
    
    Saves intent.json to <root_dir>/spec/intent.json
    """
    intent = state.get("intent")
    
    if not intent:
        # Nothing to save
        return state
    
    # Get root_dir from state
    root_dir = state.get("root_dir")
    if not root_dir:
        raise ValueError("root_dir is required in state to save intent")
    
    # Create directory structure: <root_dir>/spec/
    spec_dir = root_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    file_path = spec_dir / "intent.json"
    
    # Save intent as JSON
    with open(file_path, "w") as f:
        json.dump(intent, f, indent=4)
    
    # Return state unchanged (no saved_files tracking)
    return state


# ==================== Impact Analysis Node ====================

def impact_analysis_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Analyze impact of intent changes and determine affected layers.
    
    This node:
    - Compares existing_intent with new intent (in MODIFY mode)
    - Determines which layers need regeneration
    - Returns list of affected layer IDs
    
    In CREATE mode, returns None (all layers will be generated)
    """
    # Get stream writer for custom streaming
    writer = get_stream_writer()
    
    mode = state.get("mode")
    
    # Send custom message before execution
    if writer:
        writer({
            "message": f"🔍 Analyzing impact of changes ({mode} mode)...",
            "node": "impact_analysis",
            "status": "starting"
        })
    
    # In CREATE mode, skip impact analysis (all layers will be generated)
    if mode == "CREATE":
        result = {
            **state,
            "affected_layers": None,  # None means all layers
            "impact_analysis_changes": None,  # No changes in CREATE mode
        }
    else:
        # In MODIFY mode, perform impact analysis
        existing_intent = state.get("existing_intent")
        new_intent = state.get("intent")
        architecture = state.get("architecture")
        
        if not existing_intent or not new_intent or not architecture:
            # If we don't have enough info, regenerate all layers to be safe
            all_layer_ids = [layer.get("id") for layer in architecture.get("execution_layers", [])]
            result = {
                **state,
                "affected_layers": all_layer_ids,
                "impact_analysis_changes": None,  # Could not analyze changes
            }
        else:
            # Analyze changes
            changes = _analyze_intent_changes(existing_intent, new_intent)
            
            # Determine affected layers
            affected_layers = _determine_affected_layers(changes, architecture)
            
            result = {
                **state,
                "affected_layers": affected_layers,
                "impact_analysis_changes": changes,  # Store detailed changes for results
            }
    
    # Send custom message after execution
    if writer:
        affected_count = len(result.get("affected_layers", [])) if result.get("affected_layers") is not None else "all"
        writer({
            "message": f"✅ Impact analysis completed ({mode} mode). Affected layers: {affected_count}",
            "node": "impact_analysis",
            "status": "completed",
        })
    
    return result


def _analyze_intent_changes(old_intent: dict, new_intent: dict) -> dict:
    """Compare old and new intent to identify changes.
    
    Returns a dict with:
    - entities_added: list of new entity names
    - entities_removed: list of removed entity names
    - entities_modified: dict of entity_name -> field changes
    - operations_changed: dict of entity_name -> operation changes
    - ui_changed: bool
    """
    changes = {
        "entities_added": [],
        "entities_removed": [],
        "entities_modified": {},
        "operations_changed": {},
        "ui_changed": False,
    }
    
    # primary_entities is a list of entity objects, not a dict
    # Convert to dict keyed by entity name for easier comparison
    old_entities_list = old_intent.get("primary_entities", [])
    new_entities_list = new_intent.get("primary_entities", [])
    
    # Convert lists to dicts: {entity_name: entity_object}
    old_entities = {entity.get("name"): entity for entity in old_entities_list if entity.get("name")}
    new_entities = {entity.get("name"): entity for entity in new_entities_list if entity.get("name")}
    
    # Check for added/removed entities
    old_entity_names = set(old_entities.keys())
    new_entity_names = set(new_entities.keys())
    
    changes["entities_added"] = list(new_entity_names - old_entity_names)
    changes["entities_removed"] = list(old_entity_names - new_entity_names)
    
    # Check for modified entities (field changes)
    for entity_name in new_entity_names & old_entity_names:
        old_entity = old_entities[entity_name]
        new_entity = new_entities[entity_name]
        
        # Fields are also lists, convert to dicts for comparison
        old_fields_list = old_entity.get("fields", [])
        new_fields_list = new_entity.get("fields", [])
        
        old_fields = {field.get("name"): field for field in old_fields_list if field.get("name")}
        new_fields = {field.get("name"): field for field in new_fields_list if field.get("name")}
        
        field_changes = {
            "fields_added": [],
            "fields_removed": [],
            "fields_modified": [],
        }
        
        old_field_names = set(old_fields.keys())
        new_field_names = set(new_fields.keys())
        
        field_changes["fields_added"] = list(new_field_names - old_field_names)
        field_changes["fields_removed"] = list(old_field_names - new_field_names)
        
        # Check for modified field types/requirements
        for field_name in old_field_names & new_field_names:
            if old_fields[field_name] != new_fields[field_name]:
                field_changes["fields_modified"].append(field_name)
        
        if any(field_changes.values()):
            changes["entities_modified"][entity_name] = field_changes
    
    # Check for operation changes
    # operations is a list of objects: [{"entity_name": "Expense", "operations": ["create", "read"]}, ...]
    old_operations_list = old_intent.get("operations", [])
    new_operations_list = new_intent.get("operations", [])
    
    # Convert to dicts: {entity_name: set_of_operations}
    old_operations = {}
    for op_obj in old_operations_list:
        entity_name = op_obj.get("entity_name")
        if entity_name:
            old_operations[entity_name] = set(op_obj.get("operations", []))
    
    new_operations = {}
    for op_obj in new_operations_list:
        entity_name = op_obj.get("entity_name")
        if entity_name:
            new_operations[entity_name] = set(op_obj.get("operations", []))
    
    for entity_name in set(old_operations.keys()) | set(new_operations.keys()):
        old_ops = old_operations.get(entity_name, set())
        new_ops = new_operations.get(entity_name, set())
        
        if old_ops != new_ops:
            changes["operations_changed"][entity_name] = {
                "added": list(new_ops - old_ops),
                "removed": list(old_ops - new_ops),
            }
    
    # Check for UI changes
    old_ui = old_intent.get("ui_expectations", {})
    new_ui = new_intent.get("ui_expectations", {})
    changes["ui_changed"] = old_ui != new_ui
    
    return changes


def _determine_affected_layers(changes: dict, architecture: dict) -> list:
    """Map intent changes to affected layers.
    
    Returns list of layer IDs that need regeneration.
    """
    affected = set()
    
    # Get all layer IDs from architecture
    all_layer_ids = [layer.get("id") for layer in architecture.get("execution_layers", [])]
    
    # Rule 1: New entity added → all layers affected
    if changes["entities_added"]:
        return all_layer_ids
    
    # Rule 2: Entity removed → all layers affected (need to remove references)
    if changes["entities_removed"]:
        return all_layer_ids
    
    # Rule 3: Entity fields modified → most layers affected
    if changes["entities_modified"]:
        affected.update([
            "backend_models",    # Pydantic models need field updates
            "database",          # SQL schema needs column updates
            "backend_services",  # Service functions use models
            "backend_routes",    # Routes use models for request/response
            "frontend_ui",       # Forms need new fields
        ])
    
    # Rule 4: Operations changed → affects service/route/UI layers
    if changes["operations_changed"]:
        affected.update([
            "backend_services",  # New/removed functions
            "backend_routes",    # New/removed endpoints
            "frontend_ui",       # New/removed views
        ])
    
    # Rule 5: UI-only changes → only frontend affected
    if changes["ui_changed"] and not changes["entities_modified"] and not changes["operations_changed"]:
        affected.add("frontend_ui")
    
    # Filter to only layers that exist in architecture
    return [layer_id for layer_id in all_layer_ids if layer_id in affected]


def save_architecture_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Save architecture to spec directory using root_dir from state.
    
    Saves architecture.json to <root_dir>/spec/architecture.json
    """
    architecture = state.get("architecture")
    
    if not architecture:
        # Nothing to save
        return state
    
    # Get root_dir from state
    root_dir = state.get("root_dir")
    if not root_dir:
        raise ValueError("root_dir is required in state to save architecture")
    
    # Create directory structure: <root_dir>/spec/
    spec_dir = root_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    file_path = spec_dir / "architecture.json"
    
    # Save architecture as JSON
    with open(file_path, "w") as f:
        json.dump(architecture, f, indent=4, default=str)
    
    # Return state unchanged (no saved_files tracking)
    return state


def save_spec_plan_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Save spec plan to spec directory using root_dir from state.
    
    Saves spec_plan.json to <root_dir>/spec/spec_plan.json
    """
    spec_plan = state.get("spec_plan")
    
    if not spec_plan:
        # Nothing to save
        return state
    
    # Get root_dir from state
    root_dir = state.get("root_dir")
    if not root_dir:
        raise ValueError("root_dir is required in state to save spec_plan")
    
    # Create directory structure: <root_dir>/spec/
    spec_dir = root_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    
    # File path
    file_path = spec_dir / "spec_plan.json"
    
    # Save spec_plan as JSON
    with open(file_path, "w") as f:
        json.dump(spec_plan, f, indent=4, default=str)
    
    # Return state unchanged (no saved_files tracking)
    return state


# ==================== Finalize Node ====================

def finalize_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Finalize the code generation by creating helper files and saving existing intent/architecture.
    
    Creates:
    - requirements.txt: Python dependencies
    - run.sh: Startup script
    
    Also copies intent to existing_intent and architecture to existing_architecture for next run.
    """
    # Get stream writer for custom streaming
    writer = get_stream_writer()
    
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
# Delete existing database if it exists (for fresh initialization)
DB_PATH="$APP_DIR/app.db"
if [ -f "$DB_PATH" ]; then
    echo "Removing existing database..."
    rm -f "$DB_PATH"
    echo "✅ Existing database removed"
fi
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
    os.chmod(run_sh_path, os.stat(run_sh_path).st_mode | stat.S_IEXEC)

    # Copy intent to existing_intent and architecture to existing_architecture for next run
    intent = state.get("intent")
    architecture = state.get("architecture")
    
    # Send custom message before execution
    if writer:
        writer({
            "message": "📦 Finalizing app setup...",
            "node": "finalize",
            "status": "starting"
        })
    
    result = {
        **state,
        "requirements_text": requirements_text,
        "existing_intent": copy.deepcopy(intent) if intent else None,
        "existing_architecture": copy.deepcopy(architecture) if architecture else None,
    }
    
    # Send custom message after execution
    if writer:
        writer({
            "message": "✅ App finalization completed.",
            "node": "finalize",
            "status": "completed",
        })
    
    return result


# ==================== Code Agents Wrapper Node ====================

def code_agents_wrapper_node(state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
    """Wrapper node that maps OrchestratorState to CodeAgentsState and invokes the code agents graph.
    
    This is needed because the compiled code agents graph expects CodeAgentsState,
    but the orchestrator uses OrchestratorState.
    """
    # Map OrchestratorState to CodeAgentsState
    code_agents_input: CodeAgentsState = {
        "intent": state.get("intent"),
        "architecture": state.get("architecture"),
        "specs": state.get("spec_plan") or [],  # Map spec_plan to specs
        "manifests": [],
        "execution_queue": None,
        "next_layer_index": None,
        "root_dir": state.get("root_dir"),
        "existing_intent": state.get("existing_intent"),
        "existing_architecture": state.get("existing_architecture"),
        "affected_layers": state.get("affected_layers"),  # Pass affected_layers for selective regeneration
    }
    
    # Get the compiled code agents graph
    code_agents_graph = create_code_agents_graph()
    
    # Invoke the code agents graph
    result = code_agents_graph.invoke(code_agents_input, config=config)
    
    # Map result back to OrchestratorState
    # Just update manifests - finalization will happen in the finalize node
    return {
        **state,
        "manifests": result.get("manifests") if isinstance(result, dict) else None,
    }


# ==================== Graph Construction ====================

def create_orchestrator_graph():
    """Create and compile the orchestrator graph.
    
    Graph structure:
    initialize_graph -> intent_interpreter -> save_intent -> architect -> save_architecture 
    -> impact_analysis -> spec_planner -> save_spec_plan -> code_agents -> END
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create checkpointer for state persistence
    checkpointer = MemorySaver()
    
    # Create the graph
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes - use agents directly with system config
    workflow.add_node("initialize_graph", initialize_graph)
    
    intent_config = system_config["intent_interpreter"]
    architect_config = system_config["architect"]
    spec_planner_config = system_config["spec_planner"]
    
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
    workflow.add_node("impact_analysis", impact_analysis_node)  # NEW: Impact analysis
    workflow.add_node(
        "spec_planner",
        SpecPlannerAgent(
            provider=spec_planner_config["provider"],
            model=spec_planner_config["model"],
            additional_kwargs=spec_planner_config["additional_kwargs"],
        )
    )
    workflow.add_node("save_spec_plan", save_spec_plan_node)
    workflow.add_node("code_agents", code_agents_wrapper_node)
    workflow.add_node("finalize", finalize_node)
    
    # Set entry point
    workflow.set_entry_point("initialize_graph")
    
    # Add edges - deterministic flow
    workflow.add_edge("initialize_graph", "intent_interpreter")
    workflow.add_edge("intent_interpreter", "save_intent")
    workflow.add_edge("save_intent", "architect")
    workflow.add_edge("architect", "save_architecture")
    workflow.add_edge("save_architecture", "impact_analysis")  # NEW: Add impact analysis
    workflow.add_edge("impact_analysis", "spec_planner")
    workflow.add_edge("spec_planner", "save_spec_plan")
    workflow.add_edge("save_spec_plan", "code_agents")
    workflow.add_edge("code_agents", "finalize")
    workflow.add_edge("finalize", END)
    
    # Compile the graph
    compiled = workflow.compile(checkpointer=checkpointer)
    
    return compiled