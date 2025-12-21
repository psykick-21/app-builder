"""Pydantic models and TypedDicts for Code Generation Agents."""

from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel, Field


class CodeAgentResult(TypedDict):
    """Standard result contract for all code generation agents.
    
    Every coding agent must return this structure to enable:
    - code_map.json generation
    - Deterministic retries
    - Selective regeneration
    """
    generated_files: List[str]  # List of file paths relative to app root (e.g., ["backend/models/task.py"])
    warnings: List[str]  # List of warning messages (e.g., ["Model X uses deprecated field Y"])
    metadata: Dict[str, Any]  # Additional metadata (e.g., {"models_created": 3, "total_lines": 150})


class CodeAgentResponse(BaseModel):
    """Pydantic model for LLM structured output.
    
    This matches CodeAgentResult but uses BaseModel for structured output.
    The LLM returns code content as a dict (filename -> code), which is then
    converted to CodeAgentResult format (list of file paths).
    """
    files: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping filename to complete Python code content. Key is the filename (e.g., 'task.py'), value is the complete Python code as a string."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warning messages generated during code generation (e.g., ['Model X uses deprecated pattern Y', 'Field Z may need validation'])"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the code generation process. Common keys include: models_created (number of model classes), entities_covered (list of entity names), total_lines (approximate line count), etc."
    )
