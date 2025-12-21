"""Backend Model Agent - generates Python Pydantic model files from specifications."""

from typing import Dict, Any, Optional, Literal
import json
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
import os

from ...models.code_agents.code_agent_models import CodeAgentResult
from ...models.code_agents.backend_model_agent_models import BackendModelAgentResponse
from ...models.code_agents.code_agent_models import ManifestFile, Manifests, Manifest
from ...models.spec_planner_models import BackendModelsSpec
from ...prompts.code_agents.backend_model_agent_prompts import BACKEND_MODEL_AGENT_PROMPT
from ...utils.llm_provider import init_llm


load_dotenv()


class BackendModelAgent:
    """Agent responsible for generating backend Pydantic model files."""
    
    def __init__(
        self,
        provider: Literal["openai", "ollama"],
        model: str,
        additional_kwargs: dict,
    ):
        """Initialize the Backend Model agent.
        
        Args:
            provider: The LLM provider to use
            model: The model name to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
        # Use structured output for code generation response
        llm_with_structure = self.llm.with_structured_output(
            BackendModelAgentResponse, 
            method="function_calling"
        )
        self.chain = BACKEND_MODEL_AGENT_PROMPT | llm_with_structure
    
    def execute(
        self,
        entities: Dict[str, Any],
        backend_models_spec: BackendModelsSpec,
    ) -> BackendModelAgentResponse:
        """Execute the backend model generation logic.
        
        Args:
            entities: Entity definitions from intent.primary_entities
            backend_models_spec: The backend models specification from spec planner
            
        Returns:
            BackendModelAgentResponse with files, warnings, and metadata
        """
        # Format inputs for prompt
        spec_str = json.dumps(backend_models_spec.model_dump(), indent=2)
        entities_str = json.dumps(entities, indent=2)
        
        # Invoke the LLM chain
        response = self.chain.invoke({
            "backend_models_spec": spec_str,
            "entities_info": entities_str,
        })

        return response
    
    def __call__(
        self,
        state: Dict[str, Any],
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """LangGraph node interface (for future use).
        
        Args:
            state: Current workflow state
            config: Optional runtime configuration
            
        Returns:
            Updated state with code generation results
        """
        # Get stream writer for custom streaming
        writer = get_stream_writer()
        
        # Extract inputs from state
        entities = state.get("intent").get("primary_entities")

        current_layer_index = state.get("next_layer_index")
        execution_queue = state.get("execution_queue")
        current_layer_id, current_layer_path = execution_queue[current_layer_index]
        
        backend_models_spec = None
        for spec in state.get("specs"):
            if spec.get("layer_id") == current_layer_id:
                backend_models_spec = spec.get("spec")
                break
        
        if not backend_models_spec:
            raise ValueError("backend_models_spec is required in state")
        
        # Convert spec dict to model if needed
        if isinstance(backend_models_spec, dict):
            backend_models_spec = BackendModelsSpec(**backend_models_spec)
        
        # Send custom message before execution
        if writer:
            writer({
                "message": f"🔧 Starting backend model generation ({current_layer_id})...",
                "node": "backend_model_agent",
                "status": "starting"
            })
        
        # Execute the agent
        result = self.execute(
            entities=entities,
            backend_models_spec=backend_models_spec,
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
            spec=backend_models_spec.model_dump(),
            manifest_files=manifest_files,
        )
        
        # Send custom message after execution
        if writer:
            writer({
                "message": f"✅ Backend model generation completed ({current_layer_id}).",
                "node": "backend_model_agent",
                "status": "completed",
            })
        
        # Update state with results
        return {
            **state,
            "manifests": [manifest.model_dump()],
            "next_layer_index": current_layer_index + 1,
        }


if __name__ == "__main__":
    # Example usage
    import json
    
    # Load test data
    with open("results/spec_planner_responses.json", "r") as f:
        test_data = json.load(f)
    
    # Initialize agent
    agent = BackendModelAgent(
        provider="openai",
        model="gpt-5-mini",
        additional_kwargs={},
    )
    
    # Process all test cases
    all_results = []
    
    for idx, example in enumerate(test_data):
        print(f"Processing test case {idx + 1}/{len(test_data)}...")
        
        intent = example["intent"]
        architecture = example["architecture"]
        
        # Find backend_models spec
        backend_models_spec = None
        for spec_response in example["spec_responses"]:
            if spec_response["layer_id"] == "backend_models":
                backend_models_spec = BackendModelsSpec(**spec_response["spec"])
                break
        
        if not backend_models_spec:
            print(f"  Skipping test case {idx + 1}: No backend_models spec found")
            continue
        
        # Find backend_models layer
        backend_models_layer = None
        for layer in architecture["execution_layers"]:
            if layer["id"] == "backend_models":
                backend_models_layer = layer
                break
        
        if not backend_models_layer:
            print(f"  Skipping test case {idx + 1}: No backend_models layer found")
            continue
        
        # Execute
        try:
            result = agent.execute(
                entities=intent["primary_entities"],
                architecture_layer=backend_models_layer,
                backend_models_spec=backend_models_spec,
                app_root="temp/test_output",
            )
            
            # Add result to list with context
            all_results.append({
                **result,
                "test_case_index": idx,
                "entities": intent["primary_entities"],
                "backend_models_spec": backend_models_spec.model_dump(),
            })
            print(f"  ✓ Test case {idx + 1} completed successfully")
        except Exception as e:
            print(f"  ✗ Test case {idx + 1} failed: {str(e)}")
            continue
    
    # Save all results
    os.makedirs("results", exist_ok=True)
    with open("results/backend_model_agent_result.json", "w") as f:
        json.dump(all_results, f, indent=4)
    
    print(f"\nCompleted processing {len(all_results)}/{len(test_data)} test cases")
    print(f"Results saved to results/backend_model_agent_result.json")
