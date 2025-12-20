"""Pydantic models for Intent Interpreter."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, Dict, List

# Constants for validation
ALLOWED_FIELD_TYPES = Literal["string", "integer", "boolean", "date"]
ALLOWED_CRUD_OPERATIONS = Literal["create", "read", "update", "delete"]
ALLOWED_UI_COMPLEXITY = Literal["basic", "intermediate", "advanced", "no_ui"]
ALLOWED_INTERACTION_STYLES = Literal["form_and_list", "dashboard", "wizard", "single_page", "no_ui"]
ALLOWED_APP_CATEGORIES = Literal["crud_app", "dashboard", "form_app", "api_service", "other"]


class EntityField(BaseModel):
    """Field definition for an entity.
    
    Type Semantics:
    - 'integer': For amounts, numbers, counts
    - 'date': For dates, timestamps
    - 'boolean': For true/false, yes/no values
    - 'string': For all other text fields
    """
    
    type: ALLOWED_FIELD_TYPES = Field(
        description=(
            "The data type of the field. "
            "Use 'integer' for amounts/numbers, 'date' for dates, "
            "'boolean' for yes/no, 'string' for text."
        )
    )
    required: bool = Field(
        default=True,
        description="Whether this field is required"
    )


class PrimaryEntity(BaseModel):
    """Definition of a primary entity in the application.
    
    Rules:
    - Description must be natural language (min 10 characters)
    - Must have at least one field defined
    - Only actual domain entities allowed (Task, Bug, Note, etc.)
    """
    
    description: str = Field(
        description=(
            "Natural language description of what this entity represents. "
            "Example: 'A task with a title and description' (min 10 characters)"
        )
    )
    fields: Dict[str, EntityField] = Field(
        description="Dictionary of field names to field definitions (must have at least one field)"
    )
    
    @field_validator('description')
    @classmethod
    def validate_description_length(cls, v: str) -> str:
        """Ensure description is meaningful (not a short placeholder)."""
        min_length = 10
        if len(v.strip()) < min_length:
            raise ValueError(
                f"Entity description must be at least {min_length} characters. "
                f"Received: '{v}' ({len(v.strip())} characters). "
                f"Use descriptive text like 'A task with a title and description' instead."
            )
        return v
    
    @field_validator('fields')
    @classmethod
    def validate_fields_not_empty(cls, v: Dict[str, EntityField]) -> Dict[str, EntityField]:
        """Ensure each entity has at least one field."""
        if not v or len(v) == 0:
            raise ValueError(
                "Each entity must have at least one field. "
                "Empty fields are not allowed."
            )
        return v


class UIExpectations(BaseModel):
    """UI complexity and interaction expectations.
    
    Interaction Styles:
    - 'form_and_list': Standard CRUD apps with forms and lists
    - 'single_page': Simple single-view apps
    - 'dashboard': Data visualization focused apps
    - 'wizard': Step-by-step guided flows
    - 'no_ui': Backend-only/API services with no UI
    """
    
    complexity: ALLOWED_UI_COMPLEXITY = Field(
        default="basic",
        description="Expected UI complexity level (basic, intermediate, advanced, or no_ui for backend-only)"
    )
    interaction_style: ALLOWED_INTERACTION_STYLES = Field(
        default="form_and_list",
        description=(
            "Expected interaction style: "
            "'form_and_list' for CRUD apps, 'single_page' for simple views, "
            "'dashboard' for data viz, 'wizard' for guided flows, "
            "'no_ui' for backend-only/API services"
        )
    )


class IntentModel(BaseModel):
    """Complete intent specification schema.
    
    Critical Rules:
    1. primary_entities: Only actual domain entities (Task, Bug, etc.)
    2. operations: Keys must be entity names, values must be CRUD verbs
    3. operations: No duplicate verbs per entity
    4. assumptions: Capture user preferences about ordering/filtering here
    """
    
    app_summary: str = Field(
        description="High-level summary of what the application does"
    )
    app_category: ALLOWED_APP_CATEGORIES = Field(
        default="crud_app",
        description="Category of the application (crud_app, dashboard, form_app, api_service, or other)"
    )
    
    primary_entities: Dict[str, PrimaryEntity] = Field(
        description=(
            "Dictionary/object mapping entity names to entity definitions. "
            "MUST be a dictionary/object (NOT a list/array). "
            "Format: {'Task': {'description': '...', 'fields': {...}}, 'Bug': {...}}. "
            "Keys must be entity names (e.g., 'Task', 'Bug', 'Note'). "
            "Must NOT contain non-entities like 'operations' or 'ui_expectations'."
        )
    )
    
    operations: Dict[str, List[ALLOWED_CRUD_OPERATIONS]] = Field(
        description=(
            "Dictionary mapping entity names to their supported CRUD operations. "
            "Keys MUST be entity names from primary_entities (NOT action verbs like 'create_bug'). "
            "Values are arrays of deduplicated CRUD verbs: ['create', 'read', 'update', 'delete']."
        )
    )
    
    ui_expectations: UIExpectations = Field(
        default_factory=lambda: UIExpectations(),
        description="UI complexity and interaction expectations"
    )
    
    assumptions: List[str] = Field(
        default_factory=lambda: ["Single-user application", "Local execution"],
        description=(
            "List of assumptions about the application context. "
            "The defaults 'Single-user application' and 'Local execution' are MANDATORY and automatically included. "
            "Add additional assumptions only if there are other implicit constraints or user preferences "
            "(e.g., 'Open bugs shown first', 'Notes are plain text only')."
        )
    )
    
    non_goals: List[str] = Field(
        default_factory=list,
        description="List of explicitly excluded features or goals"
    )
    
    @model_validator(mode='after')
    def validate_operations(self):
        """Validate operations are entity-centric and properly structured."""
        entity_names = set(self.primary_entities.keys())
        operations_keys = set(self.operations.keys())
        
        # Rule 1: All operations keys must be entity names
        invalid_keys = operations_keys - entity_names
        if invalid_keys:
            raise ValueError(
                f"Operations keys must be entity names only. "
                f"Invalid keys found: {invalid_keys}. "
                f"Valid entity names are: {entity_names}. "
                f"Do not use action verbs like 'create_bug', 'list_bugs', 'create', 'edit', 'delete' as keys."
            )
        
        # Rule 2: Deduplicate operations and validate they're valid CRUD verbs
        valid_verbs = {"create", "read", "update", "delete"}
        for entity_name, verbs in self.operations.items():
            # Check for duplicates
            if len(verbs) != len(set(verbs)):
                raise ValueError(
                    f"Operations for entity '{entity_name}' contain duplicates: {verbs}. "
                    f"Each verb should appear only once."
                )
            
            # Check for invalid verbs (should be caught by Literal, but being explicit)
            invalid_verbs = set(verbs) - valid_verbs
            if invalid_verbs:
                raise ValueError(
                    f"Operations for entity '{entity_name}' contain invalid verbs: {invalid_verbs}. "
                    f"Only allowed verbs are: {valid_verbs}"
                )
        
        return self


class IntentInterpreterResponse(BaseModel):
    """Response model for Intent Interpreter agent."""
    
    mode: Literal["CREATE", "MODIFY"] = Field(
        description="The mode in which the interpreter operated"
    )
    intent: IntentModel = Field(
        description="The validated intent specification"
    )
    change_summary: str = Field(
        description="Human-readable summary of changes made (for MODIFY mode) or initial intent (for CREATE mode)"
    )

