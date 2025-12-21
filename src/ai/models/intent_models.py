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
    
    name: str = Field(
        description="The name of the field (e.g., 'title', 'description', 'status')"
    )
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
    
    name: str = Field(
        description="The name of the entity (e.g., 'Task', 'Bug', 'Note')"
    )
    description: str = Field(
        description=(
            "Natural language description of what this entity represents. "
            "Example: 'A task with a title and description' (min 10 characters)"
        )
    )
    fields: List[EntityField] = Field(
        description="List of field definitions (must have at least one field)"
    )
    id_strategy: Literal["auto_increment", "uuid", "user_provided", "natural_key"] = Field(
        default="auto_increment",
        description=(
            "Primary key generation strategy. "
            "'auto_increment': Database generates sequential IDs (default for most CRUD apps). "
            "'uuid': System generates UUIDs. "
            "'user_provided': Client provides IDs (for data imports). "
            "'natural_key': Use a field like email/username as primary key."
        )
    )
    natural_key_field: Optional[str] = Field(
        default=None,
        description="Field name to use as natural key (only if id_strategy is 'natural_key')"
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
    def validate_fields_not_empty(cls, v: List[EntityField]) -> List[EntityField]:
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
    
    complexity: Optional[ALLOWED_UI_COMPLEXITY] = Field(
        default="basic",
        description="Expected UI complexity level (basic, intermediate, advanced, or no_ui for backend-only)"
    )
    interaction_style: Optional[ALLOWED_INTERACTION_STYLES] = Field(
        default="form_and_list",
        description=(
            "Expected interaction style: "
            "'form_and_list' for CRUD apps, 'single_page' for simple views, "
            "'dashboard' for data viz, 'wizard' for guided flows, "
            "'no_ui' for backend-only/API services"
        )
    )


class EntityOperations(BaseModel):
    """Operations supported for a specific entity."""
    
    entity_name: str = Field(
        description="The name of the entity (must match a name in primary_entities)"
    )
    operations: List[ALLOWED_CRUD_OPERATIONS] = Field(
        description=(
            "List of supported CRUD operations for this entity. "
            "Values are deduplicated CRUD verbs: ['create', 'read', 'update', 'delete']."
        )
    )
    
    @field_validator('operations')
    @classmethod
    def validate_no_duplicates(cls, v: List[ALLOWED_CRUD_OPERATIONS]) -> List[ALLOWED_CRUD_OPERATIONS]:
        """Ensure operations list has no duplicates."""
        if len(v) != len(set(v)):
            raise ValueError(
                f"Operations contain duplicates: {v}. "
                f"Each verb should appear only once."
            )
        return v


class IntentModel(BaseModel):
    """Complete intent specification schema.
    
    Critical Rules:
    1. primary_entities: Only actual domain entities (Task, Bug, etc.)
    2. operations: Each entry maps entity name to CRUD verbs
    3. operations: No duplicate verbs per entity
    4. assumptions: Capture user preferences about ordering/filtering here
    """
    
    app_summary: str = Field(
        description="High-level summary of what the application does"
    )
    app_category: Optional[ALLOWED_APP_CATEGORIES] = Field(
        default="crud_app",
        description="Category of the application (crud_app, dashboard, form_app, api_service, or other)"
    )
    
    primary_entities: List[PrimaryEntity] = Field(
        description=(
            "List of primary entity definitions. "
            "Each entity must have a unique name and contain fields describing its structure. "
            "Only actual domain entities allowed (e.g., 'Task', 'Bug', 'Note'). "
            "Must NOT contain non-entities like 'operations' or 'ui_expectations'."
        )
    )
    
    operations: List[EntityOperations] = Field(
        description=(
            "List of entity operations defining which CRUD operations are supported for each entity. "
            "Each entry maps an entity name to its supported operations. "
            "Entity names MUST match names from primary_entities (NOT action verbs like 'create_bug'). "
            "Operations are deduplicated CRUD verbs: ['create', 'read', 'update', 'delete']."
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
        # Create a set of entity names from primary_entities
        entity_names = {entity.name for entity in self.primary_entities}
        
        # Get entity names from operations
        operations_entity_names = {op.entity_name for op in self.operations}
        
        # Rule 1: All operations entity_names must be valid entity names
        invalid_names = operations_entity_names - entity_names
        if invalid_names:
            raise ValueError(
                f"Operations entity_names must reference valid entities only. "
                f"Invalid entity names found: {invalid_names}. "
                f"Valid entity names are: {entity_names}. "
                f"Do not use action verbs like 'create_bug', 'list_bugs', 'create', 'edit', 'delete' as entity names."
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

