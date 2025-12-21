"""Pydantic models for Frontend Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class FrontendAgentMetadata(BaseModel):
    """Metadata specific to Frontend Agent."""
    pages_created: Optional[int] = Field(
        None,
        description="Number of pages/views generated"
    )
    entities_covered: Optional[List[str]] = Field(
        None,
        description="List of entity names that were processed"
    )
    total_lines: Optional[int] = Field(
        None,
        description="Approximate total lines of code generated"
    )
    constraints_respected: Optional[bool] = Field(
        None,
        description="Boolean indicating whether all layer constraints were followed"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous"
    )


class FrontendAgentResponse(BaseModel):
    """Pydantic model for Frontend Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "missing API endpoints, ambiguous spec interpretations, "
            "or patterns that may cause downstream issues."
        )
    )
    metadata: FrontendAgentMetadata = Field(
        default_factory=FrontendAgentMetadata,
        description=(
            "Metadata about the code generation process. "
            "All fields are optional: "
            "pages_created (int) - count of pages/views, "
            "entities_covered (List[str]) - list of entity names like ['Task'], "
            "total_lines (int) - approximate line count. "
            "Provide these fields when available."
        )
    )
