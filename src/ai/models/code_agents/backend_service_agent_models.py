"""Pydantic models for Backend Service Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendServiceAgentMetadata(BaseModel):
    """Metadata specific to Backend Service Agent."""
    services_created: int = Field(
        ...,
        description="Number of service classes generated - REQUIRED field"
    )
    entities_covered: List[str] = Field(
        ...,
        description="List of entity names that were processed - REQUIRED field"
    )
    total_lines: int = Field(
        ...,
        description="Approximate total lines of code generated - REQUIRED field"
    )
    functions_created: int = Field(
        ...,
        description="Total number of service functions generated - REQUIRED field"
    )
    operations_implemented: Dict[str, List[str]] = Field(
        ...,
        description="Dictionary mapping entity to list of operations (e.g., {'Task': ['create', 'read', 'update', 'delete']}) - REQUIRED field"
    )
    constraints_respected: Optional[bool] = Field(
        None,
        description="Boolean indicating whether all layer constraints were followed"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous (e.g., ['Assumed task_id is int type'])"
    )


class BackendServiceAgentResponse(BaseModel):
    """Pydantic model for Backend Service Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "service functions that might need validation, "
            "ambiguous spec interpretations, "
            "or patterns that may cause downstream issues. "
            "Examples: 'Service function does not validate business rules', "
            "'Update function allows all fields to be None'"
        )
    )
    metadata: BackendServiceAgentMetadata = Field(
        ...,
        description=(
            "REQUIRED: Metadata about the code generation process. "
            "You MUST provide this field with ALL required sub-fields: "
            "services_created (int) - count of service classes, "
            "entities_covered (List[str]) - list of entity names like ['Task'], "
            "total_lines (int) - approximate line count, "
            "functions_created (int) - total number of service functions, "
            "operations_implemented (Dict[str, List[str]]) - mapping like {'Task': ['create', 'read', 'update', 'delete']}. "
            "This field is MANDATORY and cannot be omitted."
        )
    )
