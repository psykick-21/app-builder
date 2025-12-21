"""Spec Planner Agent - converts intent + architecture into layer-specific execution specs."""

from typing import Dict, Any, Optional, Literal
import json
from pathlib import Path
from dotenv import load_dotenv
import os

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from pydantic import BaseModel

from ..models.spec_planner_models import (
    BackendModelsSpec,
    DatabaseSpec,
    BackendServicesSpec,
    BackendRoutesSpec,
    BackendAppBootstrapSpec,
    FrontendUISpec,
)
from ..prompts.spec_planner_prompts import SPEC_PLANNER_PROMPT
from ..utils.llm_provider import init_llm

load_dotenv()

# Map layer IDs to their response models
LAYER_SPEC_MODELS = {
    "backend_models": BackendModelsSpec,
    "database": DatabaseSpec,
    "backend_services": BackendServicesSpec,
    "backend_routes": BackendRoutesSpec,
    "backend_app": BackendAppBootstrapSpec,
    "frontend_ui": FrontendUISpec,
}


class SpecPlannerAgent:
    """Agent responsible for generating layer-specific execution specifications."""
    
    def __init__(
        self,
        provider: Literal["openai", "ollama"],
        model: str,
        additional_kwargs: dict,
    ):
        """Initialize the Spec Planner agent.
        
        Args:
            provider: The provider to use
            model: The model to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
    
    def execute(
        self,
        intent: Dict[str, Any],
        architecture: Dict[str, Any],
        layer_id: str,
        layer_constraints: Dict[str, Any]
    ) -> BaseModel:
        """Execute the spec planning logic for a specific layer.
        
        Args:
            intent: Validated intent specification dictionary
            architecture: Architecture plan dictionary
            layer_id: The layer ID to generate a spec for
            layer_constraints: Layer constraints from layer_constraints.json
            
        Returns:
            Layer-specific spec model (BackendModelsSpec, DatabaseSpec, etc.)
        """
        # Get the appropriate spec model for this layer
        if layer_id not in LAYER_SPEC_MODELS:
            raise ValueError(f"Unknown layer_id: {layer_id}")
        
        spec_model = LAYER_SPEC_MODELS[layer_id]
        
        # Find the layer in architecture
        layer_info = None
        for layer in architecture.get("execution_layers", []):
            if layer.get("id") == layer_id:
                layer_info = layer
                break
        
        if not layer_info:
            raise ValueError(f"Layer '{layer_id}' not found in architecture")
        
        # Get layer constraints
        layer_constraint = layer_constraints.get(layer_id, {})
        layer_role = layer_constraint.get("layer_role", "unknown")
        allowed = layer_constraint.get("allowed", [])
        forbidden = layer_constraint.get("forbidden", [])
        must_define = layer_constraint.get("must_define", [])
        
        # Format inputs for prompt
        intent_str = json.dumps(intent, indent=2)
        architecture_str = json.dumps(architecture, indent=2)
        
        layer_context = {
            "layer_id": layer_id,
            "layer_role": layer_role,
            "generator": layer_info.get("generator"),
            "path": layer_info.get("path"),
            "depends_on": layer_info.get("depends_on", []),
            "allowed": allowed,
            "forbidden": forbidden,
            "must_define": must_define,
        }
        layer_context_str = json.dumps(layer_context, indent=2)
        
        # Create LLM chain with the specific spec model for this layer
        llm_with_structure = self.llm.with_structured_output(spec_model, method="function_calling")
        chain = SPEC_PLANNER_PROMPT | llm_with_structure
        
        # Invoke the chain
        response = chain.invoke({
            "intent": intent_str,
            "architecture": architecture_str,
            "layer_context": layer_context_str,
            "layer_id": layer_id,
        })
        
        return response
    
    def __call__(
        self,
        state: Dict[str, Any],
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """LangGraph node interface.
        
        Args:
            state: Current workflow state containing intent, architecture, and layer_constraints
            config: Optional runtime configuration
            
        Returns:
            Updated state with spec_plan (list of all layer specs)
        """
        # Get stream writer for custom streaming
        writer = get_stream_writer()
        
        # Extract inputs from state
        intent = state.get("intent")
        architecture = state.get("architecture")
        layer_constraints = state.get("layer_constraints")
        affected_layers = state.get("affected_layers")  # None in CREATE mode, list in MODIFY mode
        mode = state.get("mode")
        root_dir = state.get("root_dir")
        
        if not intent:
            raise ValueError("intent is required in state")
        if not architecture:
            raise ValueError("architecture is required in state")
        if not layer_constraints:
            raise ValueError("layer_constraints is required in state")
        
        # Get all execution layers from architecture
        execution_layers = architecture.get("execution_layers", [])
        if not execution_layers:
            raise ValueError("architecture must contain at least one execution layer")
        
        # Send custom message before execution
        if writer:
            writer({
                "message": f"📋 Planning system specifications ({mode} mode)...",
                "node": "spec_planner",
                "status": "starting"
            })
        
        # Load existing spec plan if in MODIFY mode
        existing_spec_plan = None
        if mode == "MODIFY" and root_dir:
            spec_plan_path = root_dir / "spec" / "spec_plan.json"
            if spec_plan_path.exists():
                with open(spec_plan_path, "r") as f:
                    existing_spec_plan = json.load(f)
        
        # Build spec plan
        spec_plan = []
        for layer in execution_layers:
            layer_id = layer.get("id")
            if not layer_id:
                raise ValueError(f"Layer missing 'id' field: {layer}")
            
            # Check if we need to regenerate this layer
            should_regenerate = (
                mode == "CREATE" or  # CREATE mode: generate all
                affected_layers is None or  # No impact analysis: generate all
                layer_id in affected_layers  # Layer is affected
            )
            
            if should_regenerate:
                # Regenerate spec for this layer
                response = self.execute(
                    intent=intent,
                    architecture=architecture,
                    layer_id=layer_id,
                    layer_constraints=layer_constraints
                )
                
                # Validate response
                if not isinstance(response, BaseModel):
                    raise ValueError(f"Unexpected response type for layer '{layer_id}': {type(response)}")
                
                # Add to spec plan
                spec_plan.append({
                    "layer_id": layer_id,
                    "spec": response.model_dump(),
                })
            else:
                # Reuse existing spec for this layer
                if existing_spec_plan:
                    existing_layer_spec = next(
                        (spec for spec in existing_spec_plan if spec.get("layer_id") == layer_id),
                        None
                    )
                    if existing_layer_spec:
                        spec_plan.append(existing_layer_spec)
                    else:
                        # Fallback: regenerate if not found
                        response = self.execute(
                            intent=intent,
                            architecture=architecture,
                            layer_id=layer_id,
                            layer_constraints=layer_constraints
                        )
                        spec_plan.append({
                            "layer_id": layer_id,
                            "spec": response.model_dump(),
                        })
                else:
                    # No existing spec plan, regenerate
                    response = self.execute(
                        intent=intent,
                        architecture=architecture,
                        layer_id=layer_id,
                        layer_constraints=layer_constraints
                    )
                    spec_plan.append({
                        "layer_id": layer_id,
                        "spec": response.model_dump(),
                    })
        
        # Send custom message after execution
        if writer:
            writer({
                "message": f"✅ Spec planning completed ({mode} mode).",
                "node": "spec_planner",
                "status": "completed",
            })
        
        # Update state with all layer specs
        return {
            **state,
            "spec_plan": spec_plan,
        }


if __name__ == "__main__":
    import json
    from tqdm import tqdm

    with open("src/ai/utils/layer_constraints.json", "r") as f:
        layer_constraints = json.load(f)

    with open("results/orchestrator_results.json", "r") as f:
        orchestrator_results = json.load(f)

    spec_planner_agent = SpecPlannerAgent(
        provider="openai",
        model="gpt-5-mini",
        additional_kwargs={
            "reasoning_effort": "low",
        },
    )
    final_responses = []

    for orchestrator_result in tqdm(orchestrator_results):
        intent = orchestrator_result["intent"]
        architecture = orchestrator_result["architecture"]
        spec_responses = []
        for layer in tqdm(architecture["execution_layers"]):
            response = spec_planner_agent.execute(
                intent=intent, 
                architecture=architecture, 
                layer_id=layer["id"],
                layer_constraints=layer_constraints[layer["id"]]
            )
            spec_responses.append({
                "layer_id": layer["id"],
                "spec": response.model_dump()
            })
        final_responses.append({
            "intent": intent,
            "architecture": architecture,
            "spec_responses": spec_responses
        })

    os.makedirs("results", exist_ok=True)
    with open("results/spec_planner_responses.json", "w") as f:
        json.dump(final_responses, f, indent=4)
