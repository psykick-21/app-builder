"""Pydantic models for Backend Router Agent."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendRouterAgentMetadata(BaseModel):
    """Metadata specific to Backend Router Agent."""
    routers_created: Optional[int] = Field(
        None,
        description="Number of router files generated"
    )
    routes_created: Optional[int] = Field(
        None,
        description="Total number of routes generated"
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
        default_factory=BackendRouterAgentMetadata,
        description=(
            "Metadata about the code generation process. "
            "All fields are optional: "
            "routers_created (int) - count of router files, "
            "routes_created (int) - total number of routes, "
            "entities_covered (List[str]) - list of entity names like ['Task'], "
            "total_lines (int) - approximate line count. "
            "Provide these fields when available."
        )
    )
