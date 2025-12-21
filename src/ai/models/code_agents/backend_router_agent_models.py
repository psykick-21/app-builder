"""Pydantic models for Backend Router Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendRouterAgentMetadata(BaseModel):
    """Metadata specific to Backend Router Agent."""
    routers_created: int = Field(
        ...,
        description="Number of router files generated - REQUIRED field"
    )
    routes_created: int = Field(
        ...,
        description="Total number of routes generated - REQUIRED field"
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
        description="Boolean indicating whether all layer constraints were followed"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous"
    )


class BackendRouterAgentResponse(BaseModel):
    """Pydantic model for Backend Router Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "routes that might need authentication, "
            "ambiguous spec interpretations, "
            "or patterns that may cause downstream issues."
        )
    )
    metadata: BackendRouterAgentMetadata = Field(
        ...,
        description=(
            "REQUIRED: Metadata about the code generation process. "
            "You MUST provide this field with ALL required sub-fields: "
            "routers_created (int) - count of router files, "
            "routes_created (int) - total number of routes, "
            "entities_covered (List[str]) - list of entity names like ['Task'], "
            "total_lines (int) - approximate line count. "
            "This field is MANDATORY and cannot be omitted."
        )
    )
