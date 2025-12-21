"""Backend Service Agent - generates Python service files from specifications."""

from typing import Dict, Any, Optional, Literal
import json
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
import os

from ...models.code_agents.code_agent_models import ManifestFile, Manifest
from ...models.code_agents.backend_service_agent_models import BackendServiceAgentResponse
from ...models.spec_planner_models import BackendServicesSpec
from ...prompts.code_agents.backend_service_agent_prompts import BACKEND_SERVICE_AGENT_PROMPT
from ...utils.llm_provider import init_llm

load_dotenv()


class BackendServiceAgent:
    """Agent responsible for generating backend service files."""
    
    def __init__(
        self,
        provider: Literal["openai", "ollama"],
        model: str,
        additional_kwargs: dict,
    ):
        """Initialize the Backend Service agent.
        
        Args:
            provider: The LLM provider to use
            model: The model name to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
        # Use structured output for code generation response
        llm_with_structure = self.llm.with_structured_output(
            BackendServiceAgentResponse, 
            method="function_calling"
        )
        self.chain = BACKEND_SERVICE_AGENT_PROMPT | llm_with_structure
    
    def execute(
        self,
        entities: Dict[str, Any],
        backend_services_spec: BackendServicesSpec,
        manifests: list,
    ) -> BackendServiceAgentResponse:
        """Execute the backend service generation logic.
        
        Args:
            entities: Entity definitions from intent.primary_entities
            backend_services_spec: The backend services specification from spec planner
            manifests: List of manifests from previous agents
            
        Returns:
            BackendServiceAgentResponse with files, warnings, and metadata
        """
        # Format inputs for prompt
        spec_str = json.dumps(backend_services_spec.model_dump(), indent=2)
        entities_str = json.dumps(entities, indent=2)
        manifests_str = json.dumps(manifests, indent=2)
        
        # Invoke the LLM chain
        response = self.chain.invoke({
            "backend_services_spec": spec_str,
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
        
        backend_services_spec = None
        for spec in state.get("specs"):
            if spec.get("layer_id") == current_layer_id:
                backend_services_spec = spec.get("spec")
                break
        
        if not backend_services_spec:
            raise ValueError("backend_services_spec is required in state")
        
        # Convert spec dict to model if needed
        if isinstance(backend_services_spec, dict):
            backend_services_spec = BackendServicesSpec(**backend_services_spec)
        
        # Get stream writer for custom streaming
        writer = get_stream_writer()
        
        # Send custom message before execution
        message_start = f"🔧 Starting backend service generation ({current_layer_id})..."
        if writer:
            writer({
                "message": message_start,
                "node": "backend_service_agent",
                "status": "starting"
            })
        print(message_start)
        
        # Execute the agent
        result = self.execute(
            entities=entities,
            backend_services_spec=backend_services_spec,
            manifests=manifests,
        )
        
        # Get root_dir from state
        root_dir = state.get("root_dir")
        if not root_dir:
            raise ValueError("root_dir is required in state")

        file_root_path = root_dir / current_layer_path
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
            relative_file_path = os.path.join(current_layer_path, filename)
            
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
            spec=backend_services_spec.model_dump(),
            manifest_files=manifest_files,
        )
        
        # Send custom message after execution
        message_complete = f"✅ Backend service generation completed ({current_layer_id})."
        if writer:
            writer({
                "message": message_complete,
                "node": "backend_service_agent",
                "status": "completed",
            })
        print(message_complete)
        
        # Update state with results
        return {
            **state,
            "manifests": state.get("manifests", []) + [manifest.model_dump()],
            "next_layer_index": current_layer_index + 1,
        }


if __name__ == "__main__":
    # Example usage
    import json
    
    # Load test data
    with open("temp/test_data/spec_planner_responses.json", "r") as f:
        test_data = json.load(f)
    
    # Initialize agent
    agent = BackendServiceAgent(
        provider="openai",
        model="gpt-4o-mini",
        additional_kwargs={},
    )
    
    # Process only the first test case
    if not test_data:
        print("No test data found")
        exit(1)
    
    example = test_data[0]
    idx = 0
    
    print(f"Processing test case {idx + 1}...")
    
    intent = example["intent"]
    architecture = example["architecture"]
    
    # Find backend_services spec
    backend_services_spec = None
    for spec_response in example["spec_responses"]:
        if spec_response["layer_id"] == "backend_services":
            backend_services_spec = BackendServicesSpec(**spec_response["spec"])
            break
    
    if not backend_services_spec:
        print(f"  ✗ Test case {idx + 1}: No backend_services spec found")
        exit(1)
    
    # Find backend_services layer
    backend_services_layer = None
    for layer in architecture["execution_layers"]:
        if layer["id"] == "backend_services":
            backend_services_layer = layer
            break
    
    if not backend_services_layer:
        print(f"  ✗ Test case {idx + 1}: No backend_services layer found")
        exit(1)
    
    # Try to get backend_models_info from previous agent results if available
    backend_models_info = None
    # This would typically come from the BackendModelAgent results
    # For now, we'll pass None and let the agent infer from the spec
    
    # Execute
    try:
        result = agent.execute(
            entities=intent["primary_entities"],
            architecture_layer=backend_services_layer,
            backend_services_spec=backend_services_spec,
            backend_models_info=backend_models_info,
            app_root="temp/test_output",
        )
        
        # Save result
        result_with_context = {
            **result,
            "test_case_index": idx,
            "entities": intent["primary_entities"],
            "backend_services_spec": backend_services_spec.model_dump(),
        }
        
        with open("temp/test_data/backend_service_agent_result.json", "w") as f:
            json.dump(result_with_context, f, indent=4)
        
        print(f"  ✓ Test case {idx + 1} completed successfully")
        print(f"Results saved to temp/test_data/backend_service_agent_result.json")
    except Exception as e:
        print(f"  ✗ Test case {idx + 1} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
