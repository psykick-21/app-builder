"""Backend App Agent - generates FastAPI application entrypoint from specifications."""

from typing import Dict, Any, Optional, Literal
import json
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
import os

from ...models.code_agents.code_agent_models import ManifestFile, Manifest
from ...models.code_agents.backend_app_agent_models import BackendAppAgentResponse
from ...models.spec_planner_models import BackendAppBootstrapSpec
from ...prompts.code_agents.backend_app_agent_prompts import BACKEND_APP_AGENT_PROMPT
from ...utils.llm_provider import init_llm

load_dotenv()


class BackendAppAgent:
    """Agent responsible for generating FastAPI application entrypoint."""
    
    def __init__(
        self,
        provider: Literal["openai", "ollama"],
        model: str,
        additional_kwargs: dict,
    ):
        """Initialize the Backend App agent.
        
        Args:
            provider: The LLM provider to use
            model: The model name to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
        # Use structured output for code generation response
        llm_with_structure = self.llm.with_structured_output(
            BackendAppAgentResponse, 
            method="function_calling"
        )
        self.chain = BACKEND_APP_AGENT_PROMPT | llm_with_structure
    
    def execute(
        self,
        entities: Dict[str, Any],
        backend_app_spec: BackendAppBootstrapSpec,
        manifests: list,
    ) -> BackendAppAgentResponse:
        """Execute the backend app generation logic.
        
        Args:
            entities: Entity definitions from intent.primary_entities
            backend_app_spec: The backend app specification from spec planner
            manifests: List of manifests from previous agents
            
        Returns:
            BackendAppAgentResponse with files, warnings, and metadata
        """
        # Format inputs for prompt
        spec_str = json.dumps(backend_app_spec.model_dump(), indent=2)
        entities_str = json.dumps(entities, indent=2)
        manifests_str = json.dumps(manifests, indent=2)
        
        # Invoke the LLM chain
        response = self.chain.invoke({
            "backend_app_spec": spec_str,
            "entities_info": entities_str,
            "manifests_info": manifests_str,
        })

        return response
    
    def __call__(
        self,
        state: Dict[str, Any],
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """LangGraph node interface.
        
        Args:
            state: Current workflow state
            config: Optional runtime configuration
            
        Returns:
            Updated state with code generation results
        """
        # Extract inputs from state
        entities = state.get("intent").get("primary_entities")
        manifests = state.get("manifests", [])

        current_layer_index = state.get("next_layer_index")
        execution_queue = state.get("execution_queue")
        current_layer_id, current_layer_path = execution_queue[current_layer_index]
        
        backend_app_spec = None
        for spec in state.get("specs"):
            if spec.get("layer_id") == current_layer_id:
                backend_app_spec = spec.get("spec")
                break
        
        if not backend_app_spec:
            raise ValueError("backend_app_spec is required in state")
        
        # Convert spec dict to model if needed
        if isinstance(backend_app_spec, dict):
            backend_app_spec = BackendAppBootstrapSpec(**backend_app_spec)
        
        # Get stream writer for custom streaming
        writer = get_stream_writer()
        
        # Send custom message before execution
        if writer:
            writer({
                "message": f"🔧 Starting backend app bootstrap generation ({current_layer_id})...",
                "node": "backend_app_agent",
                "status": "starting"
            })
        
        # Execute the agent
        result = self.execute(
            entities=entities,
            backend_app_spec=backend_app_spec,
            manifests=manifests,
        )
        
        # Get root_dir from state
        root_dir = state.get("root_dir")
        if not root_dir:
            raise ValueError("root_dir is required in state")

        file_root_path = root_dir / current_layer_path
        # If the layer path includes a filename (e.g., backend/main.py), extract just the directory
        if file_root_path.suffix == '.py':
            file_root_path = file_root_path.parent
        file_root_path.mkdir(parents=True, exist_ok=True)

        # save files to filesystem
        for file in result.files:
            # Extract just the filename in case LLM returns a path
            filename = os.path.basename(file.filename)
            with open(file_root_path / filename, "w") as f:
                f.write(file.code_content)

        manifest_files = []
        for file in result.files:
            # Extract just the filename in case LLM returns a path
            filename = os.path.basename(file.filename)
            # Use the corrected layer path (without .py extension if it had one)
            corrected_layer_path = current_layer_path if not current_layer_path.endswith('.py') else os.path.dirname(current_layer_path)
            relative_file_path = os.path.join(corrected_layer_path, filename)
            
            manifest_file = ManifestFile(
                file_path=relative_file_path,
                imports=file.imports,
                exports=file.exports,
                dependencies=file.dependencies,
                summary=file.summary,
            )

            manifest_files.append(manifest_file)

        manifest = Manifest(
            layer_id=current_layer_id,
            spec=backend_app_spec.model_dump(),
            manifest_files=manifest_files,
        )
        
        # Send custom message after execution
        if writer:
            writer({
                "message": f"✅ Backend app bootstrap generation completed ({current_layer_id}).",
                "node": "backend_app_agent",
                "status": "completed",
            })
        
        # Update state with results
        return {
            **state,
            "manifests": state.get("manifests", []) + [manifest.model_dump()],
            "next_layer_index": current_layer_index + 1,
        }
