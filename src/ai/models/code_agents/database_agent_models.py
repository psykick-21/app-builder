"""Pydantic models for Database Agent."""

from typing import List, Optional
from pydantic import BaseModel, Field

from .code_agent_models import GeneratedFile


class DatabaseAgentMetadata(BaseModel):
    """Metadata specific to Database Agent."""
    tables_created: int = Field(
        ...,
        description="Number of database tables created - REQUIRED field"
    )
    repositories_created: int = Field(
        ...,
        description="Number of repository classes generated - REQUIRED field"
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
        description="Boolean indicating whether all layer constraints were followed (e.g., SQLite only, no migration engine)"
    )
    assumptions_made: Optional[List[str]] = Field(
        None,
        description="List of assumptions made when spec was ambiguous"
    )


class DatabaseAgentResponse(BaseModel):
    """Pydantic model for Database Agent LLM structured output."""
    files: List[GeneratedFile] = Field(
        ...,
        description="List of generated files, each containing filename and code_content"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "List of warning messages generated during code generation. "
            "IMPORTANT: Always emit warnings for potential issues like: "
            "missing indexes, potential performance issues, "
            "ambiguous spec interpretations, "
            "or patterns that may cause downstream issues."
        )
    )
    metadata: DatabaseAgentMetadata = Field(
        ...,
        description=(
            "Metadata about the code generation process. "
            "IMPORTANT: You MUST populate all required fields: "
            "tables_created (int), repositories_created (int), entities_covered (List[str]), total_lines (int). "
            "These fields are REQUIRED and must be provided in your response."
        )
    )
