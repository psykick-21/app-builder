"""Pydantic models for Architect Agent."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Dict, Any, Optional

# Constants for validation
ALLOWED_LAYER_TYPES = Literal["code_generation"]
ALLOWED_BACKEND_TECHS = Literal["fastapi"]
ALLOWED_FRONTEND_TECHS = Literal["streamlit"]


class TechStack(BaseModel):
    """Technology stack selection for the application.
    
    Select technologies based on what components the application needs:
    - Set backend when the application has server-side logic, APIs, or data processing
    - Set frontend when the application has a user interface
    - Both can be set for full-stack applications
    - Either can be None if that component is not required
    - At least one must be specified
    """
    
    backend: Optional[ALLOWED_BACKEND_TECHS] = Field(
        default=None,
        description="Backend framework to use. Set to 'fastapi' when the application needs server-side logic, APIs, data storage/retrieval, or data processing. IMPORTANT: Read-only data still requires a backend. Set to None ONLY when no data storage or processing is needed."
    )
    frontend: Optional[ALLOWED_FRONTEND_TECHS] = Field(
        default=None,
        description="Frontend framework to use. Set to 'streamlit' when the application needs a user interface. Set to None when no UI is required."
    )
    
    @field_validator('frontend')
    @classmethod
    def validate_at_least_one_component(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one of backend or frontend is specified."""
        backend = info.data.get('backend')
        if backend is None and v is None:
            raise ValueError(
                "At least one of backend or frontend must be specified. "
                "An application needs either backend logic or a user interface (or both)."
            )
        return v


class ExecutionLayer(BaseModel):
    """An execution layer in the architecture plan.
    
    Each layer:
    - Maps to exactly one generator agent from the registry
    - Owns a specific filesystem subtree
    - Declares its MINIMAL upstream dependencies (only direct imports)
    
    EXAMPLE ARCHITECTURES (adjust based on intent requirements):
    
    Full-stack application with data persistence:
    - backend_models → database → backend_services → backend_routes → backend_app
    - frontend_ui (depends on: backend_routes)
    - Tech stack: backend=fastapi, frontend=streamlit
    
    Backend-only API (no UI):
    - backend_models → database → backend_services → backend_routes → backend_app
    - Tech stack: backend=fastapi, frontend=None
    
    Frontend-only application (NO data persistence):
    - frontend_ui (no dependencies)
    - Tech stack: backend=None, frontend=streamlit
    - Use ONLY when data lives purely in browser memory with no persistence
    
    Read-only dashboard or data viewer:
    - backend_models → database → backend_services → backend_routes → backend_app
    - frontend_ui (depends on: backend_routes)
    - Tech stack: backend=fastapi, frontend=streamlit
    - Services/routes are read-only but backend structure is still required for data access
    
    Include only the layers and technologies that the intent requires.
    """
    
    id: str = Field(
        description=(
            "Stable, descriptive identifier for this layer (primary orchestration key). "
            "Use clear, conventional names like 'backend_models', 'backend_services', "
            "'backend_routes', 'backend_app', 'frontend_ui', 'database'. "
            "Once created, this ID should remain stable across iterations."
        )
    )
    type: ALLOWED_LAYER_TYPES = Field(
        default="code_generation",
        description="Layer category (code_generation for MVP)"
    )
    generator: str = Field(
        description=(
            "Agent ID selected from the agent registry. "
            "Must match an agent_id in the provided registry."
        )
    )
    path: str = Field(
        description=(
            "Filesystem root owned by this layer. "
            "Relative path from the app root (e.g., 'backend/models', 'frontend')."
        )
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description=(
            "List of MINIMAL upstream layer IDs that this layer DIRECTLY depends on. "
            "Only declare dependencies for what this layer directly imports. "
            "Empty list means no dependencies. "
            "DO NOT over-declare transitive dependencies."
        )
    )
    
    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID is a valid identifier."""
        if not v or not v.strip():
            raise ValueError("Layer ID cannot be empty")
        if ' ' in v:
            raise ValueError("Layer ID cannot contain spaces")
        return v.strip()
    
    @field_validator('depends_on')
    @classmethod
    def validate_no_self_dependency(cls, v: List[str], info) -> List[str]:
        """Ensure layer doesn't depend on itself."""
        if hasattr(info, 'data') and 'id' in info.data:
            layer_id = info.data['id']
            if layer_id in v:
                raise ValueError(f"Layer '{layer_id}' cannot depend on itself")
        return v


class ArchitectResponse(BaseModel):
    """Response model for Architect Agent."""
    
    architecture_version: str = Field(
        default="1.0",
        description="Version of the architecture schema"
    )
    tech_stack: TechStack = Field(
        description="Selected technology stack for the application"
    )
    execution_layers: List[ExecutionLayer] = Field(
        description=(
            "List of execution layers defining the architecture. "
            "Each layer maps to a generator agent and declares dependencies."
        )
    )
    
    @field_validator('execution_layers')
    @classmethod
    def validate_layers(cls, v: List[ExecutionLayer]) -> List[ExecutionLayer]:
        """Validate execution layers for basic correctness."""
        if not v:
            raise ValueError("At least one execution layer is required")
        
        # Check for duplicate IDs
        layer_ids = [layer.id for layer in v]
        if len(layer_ids) != len(set(layer_ids)):
            duplicates = [lid for lid in layer_ids if layer_ids.count(lid) > 1]
            raise ValueError(
                f"Duplicate layer IDs found: {set(duplicates)}. "
                f"Each layer must have a unique ID."
            )
        
        # Validate dependencies reference existing layers
        all_layer_ids = set(layer_ids)
        for layer in v:
            invalid_deps = set(layer.depends_on) - all_layer_ids
            if invalid_deps:
                raise ValueError(
                    f"Layer '{layer.id}' has invalid dependencies: {invalid_deps}. "
                    f"All dependencies must reference existing layer IDs."
                )
        
        # Check for circular dependencies (basic check)
        for layer in v:
            if layer.id in layer.depends_on:
                raise ValueError(
                    f"Layer '{layer.id}' cannot depend on itself"
                )
        
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "architecture_version": self.architecture_version,
            "tech_stack": {
                "backend": self.tech_stack.backend,
                "frontend": self.tech_stack.frontend,
            },
            "execution_layers": [
                {
                    "id": layer.id,
                    "type": layer.type,
                    "generator": layer.generator,
                    "path": layer.path,
                    "depends_on": layer.depends_on,
                }
                for layer in self.execution_layers
            ]
        }
