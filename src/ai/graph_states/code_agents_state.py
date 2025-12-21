"""State schema for the code agents graph."""

from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict, Annotated
import operator
from pathlib import Path


class CodeAgentsState(TypedDict, total=False):
    """
    State schema for the code agents workflow.
    """
    
    # === Input Data ===
    intent: Optional[Dict[str, Any]]  # Intent specification
    architecture: Optional[Dict[str, Any]]  # Architecture plan
    specs: Optional[List[Dict[str, Any]]]  # Specs of the layers
    manifests: Optional[List[Dict[str, Any]]]  # Manifest of tasks/items

    # === To determine execution order ===
    execution_queue: Optional[List[str]]  # List of layer IDs in execution order
    next_layer_index: Optional[int]  # Index of the next layer to execute
    
    # === Finalization ===
    requirements_text: Optional[str]  # Requirements.txt-like text with all dependencies

    # === Root Directory ===
    root_dir: Optional[Path]  # Root directory for the app
