"""Flexible state schema for the orchestrator graph that evolves as agents are added."""

from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage
import operator
from pathlib import Path


class OrchestratorState(TypedDict, total=False):
    """Flexible state schema for the orchestrator workflow.
    
    This state is designed to evolve as we add more agents to the graph.
    Fields are optional to allow incremental addition of agents without
    breaking existing functionality.
    """
    
    # === User Input ===
    raw_user_input: Optional[str]  # For CREATE mode (initial app description)
    user_feedback: Optional[str]  # For MODIFY mode (feedback for changes)
    existing_intent: Optional[Dict[str, Any]]  # For MODIFY mode (current intent before modification)
    
    # === Intent Interpreter Agent Output ===
    intent: Optional[Dict[str, Any]]  # Validated intent specification
    mode: Optional[str]  # "CREATE" or "MODIFY"
    change_summary: Optional[str]  # Human-readable change summary
    
    # === Architect Agent Output ===
    architecture: Optional[Dict[str, Any]]  # Architecture plan with execution layers
    existing_architecture: Optional[Dict[str, Any]]  # For ITERATIVE mode
    
    # === Spec Planner Agent Output ===
    spec_plan: Optional[List[Dict[str, Any]]]  # List of layer-specific execution specs
    
    # === Impact Analysis Output ===
    affected_layers: Optional[List[str]]  # List of layer IDs affected by intent changes (for MODIFY mode)
    impact_analysis_changes: Optional[Dict[str, Any]]  # Detailed changes detected during impact analysis (for MODIFY mode)
    
    # === Code Agents Graph Output ===
    manifests: Optional[List[Dict[str, Any]]]  # Manifest of tasks/items populated by code agents
    
    # === Finalization ===
    requirements_text: Optional[str]  # Requirements.txt-like text with all dependencies
    
    # === System Configuration ===
    agent_registry: Optional[List[Dict[str, Any]]]  # Available generator agents
    layer_constraints: Optional[Dict[str, Any]]  # Layer constraints from layer_constraints.json

    # === Root Directory ===
    root_dir: Optional[Path]  # Root directory for the app
