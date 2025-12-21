"""Pydantic models for Backend App Agent."""

from typing import List, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class BackendAppAgentMetadata(BaseModel):
    """Metadata specific to Backend App Agent."""
    app_created: Optional[bool] = Field(
        None,
        description="Whether the app bootstrap file was created"
    )
    routers_registered: Optional[int] = Field(
        None,
        description="Number of routers registered in the app"
    )
    total_lines: Optional[int] = Field(
        None,
        description="Approximate total lines of code generated"
    )
    middleware_configured: Optional[List[str]] = Field(
        None,
        description="List of middleware configured (if any)"
    )
    constraints_respected: Optional[bool] = Field(
        None,
        description="Boolean indicating whether all layer constraints were followed"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous"
    )


class BackendAppAgentResponse(BaseModel):
    """Pydantic model for Backend App Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "missing middleware, ambiguous spec interpretations, "
            "or patterns that may cause downstream issues."
        )
    )
    metadata: BackendAppAgentMetadata = Field(
        default_factory=BackendAppAgentMetadata,
        description=(
            "Metadata about the code generation process. "
            "All fields are optional: "
            "app_created (bool) - whether app was created, "
            "routers_registered (int) - number of routers registered, "
            "total_lines (int) - approximate line count, "
            "middleware_configured (List[str]) - list of middleware configured. "
            "Provide these fields when available."
        )
    )
