"""Pydantic models for Backend Service Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendServiceAgentMetadata(BaseModel):
    """Metadata specific to Backend Service Agent."""
    services_created: Optional[int] = Field(
        None,
        description="Number of service classes generated"
    )
    entities_covered: Optional[List[str]] = Field(
        None,
        description="List of entity names that were processed"
    )
    total_lines: Optional[int] = Field(
        None,
        description="Approximate total lines of code generated"
    )
    functions_created: Optional[int] = Field(
        None,
        description="Total number of service functions generated"
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
        default_factory=BackendServiceAgentMetadata,
        description=(
            "Metadata about the code generation process. "
            "All fields are optional: "
            "services_created (int) - count of service classes, "
            "entities_covered (List[str]) - list of entity names like ['Task'], "
            "total_lines (int) - approximate line count, "
            "functions_created (int) - total number of service functions. "
            "Provide these fields when available."
        )
    )
