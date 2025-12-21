"""State schema for the code agents graph."""

from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict, Annotated
import operator


class CodeAgentsState(TypedDict, total=False):
    """
    State schema for the code agents workflow.
    """
    
    # === Input Data ===
    intent: Optional[Dict[str, Any]]  # Intent specification
    architecture: Optional[Dict[str, Any]]  # Architecture plan
    specs: Optional[List[Dict[str, Any]]]  # Specs of the layers
    manifests: Annotated[Optional[List[Dict[str, Any]]], operator.add]  # Manifest of tasks/items

    # === To determine execution order ===
    execution_queue: Optional[List[str]]  # List of layer IDs in execution order
    next_layer_index: Optional[int]  # Index of the next layer to execute
