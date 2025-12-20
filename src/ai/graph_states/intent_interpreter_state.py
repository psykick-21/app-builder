"""State schema for Intent Interpreter."""

from typing import Optional
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage
import operator


class IntentInterpreterState(TypedDict, total=False):
    """State schema for Intent Interpreter workflow."""
    
    # Messages list (LangGraph standard)
    messages: Annotated[list[AnyMessage], operator.add]
    
    # Input fields
    raw_user_input: Optional[str]  # For CREATE mode
    user_feedback: Optional[str]  # For MODIFY mode
    existing_intent: Optional[dict]  # For MODIFY mode
    
    # Mode determination
    mode: Optional[str]  # "CREATE" or "MODIFY"
    
    # Output fields
    intent: Optional[dict]  # Validated intent specification
    change_summary: Optional[str]  # Human-readable change summary
    
    # Application context
    app_id: Optional[str]  # Application identifier for artifact persistence
    
    # Tracking metadata (standard across all workflows)
    _tracking_metadata: Optional[dict]
    
    # Config for checkpointing
    _config: Optional[dict]

