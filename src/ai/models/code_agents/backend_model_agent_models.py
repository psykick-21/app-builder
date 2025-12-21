"""Pydantic models for Backend Model Agent."""

from typing import List, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendModelAgentMetadata(BaseModel):
    """Metadata specific to Backend Model Agent."""
    models_created: int = Field(
        ...,
        description="Number of model classes generated - REQUIRED field"
    )
    entities_covered: List[str] = Field(
        ...,
        description="List of entity names that were processed - REQUIRED field"
    )
    total_lines: int = Field(
        ...,
        description="Approximate total lines of code generated - REQUIRED field"
    )
    constraints_respected: Optional[bool] = Field(
        None,
        description="Boolean indicating whether all layer constraints were followed (e.g., no id fields, extra='forbid' on input models)"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous (e.g., ['Assumed status defaults to pending'])"
    )


class BackendModelAgentResponse(BaseModel):
    """Pydantic model for Backend Model Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "fields that accept any value without validation, "
            "missing format validation (e.g., email, URL), "
            "ambiguous spec interpretations, "
            "or patterns that may cause downstream issues. "
            "Examples: 'Task.status accepts any string; recommend enum validation', "
            "'User.email has no format validation; consider EmailStr type'"
        )
    )
    metadata: BackendModelAgentMetadata = Field(
        ...,
        description=(
            "Metadata about the code generation process. "
            "IMPORTANT: You MUST populate all required fields: "
            "models_created (int), entities_covered (List[str]), total_lines (int). "
            "These fields are REQUIRED and must be provided in your response."
        )
    )
