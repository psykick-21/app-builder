"""Database Agent - generates SQLite database setup and repository classes from specifications."""

from typing import Dict, Any, Optional, Literal
import json
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.runnables import RunnableConfig
import os

from ...models.code_agents.code_agent_models import ManifestFile, Manifest
from ...models.code_agents.database_agent_models import DatabaseAgentResponse
from ...models.spec_planner_models import DatabaseSpec
from ...prompts.code_agents.database_agent_prompts import DATABASE_AGENT_PROMPT
from ...utils.llm_provider import init_llm


load_dotenv()


class DatabaseAgent:
    """Agent responsible for generating SQLite database setup and repository classes."""
    
    def __init__(
        self,
        provider: Literal["openai", "ollama"],
        model: str,
        additional_kwargs: dict,
    ):
        """Initialize the Database agent.
        
        Args:
            provider: The LLM provider to use
            model: The model name to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
        # Use structured output for code generation response
        llm_with_structure = self.llm.with_structured_output(
            DatabaseAgentResponse, 
            method="function_calling"
        )
        self.chain = DATABASE_AGENT_PROMPT | llm_with_structure
    
    def execute(
        self,
        entities: Dict[str, Any],
        database_spec: DatabaseSpec,
        manifests: list,
    ) -> DatabaseAgentResponse:
        """Execute the database generation logic.
        
        Args:
            entities: Entity definitions from intent.primary_entities
            database_spec: The database specification from spec planner
            manifests: List of manifests from previous agents
            
        Returns:
            DatabaseAgentResponse with files, warnings, and metadata
        """
        # Format inputs for prompt
        spec_str = json.dumps(database_spec.model_dump(), indent=2)
        entities_str = json.dumps(entities, indent=2)
        manifests_str = json.dumps(manifests, indent=2)
        
        # Invoke the LLM chain
        response = self.chain.invoke({
            "database_spec": spec_str,
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
        
        database_spec = None
        for spec in state.get("specs"):
            if spec.get("layer_id") == current_layer_id:
                database_spec = spec.get("spec")
                break
        
        if not database_spec:
            raise ValueError("database_spec is required in state")
        
        # Convert spec dict to model if needed
        if isinstance(database_spec, dict):
            database_spec = DatabaseSpec(**database_spec)
        
        # Execute the agent
        result = self.execute(
            entities=entities,
            database_spec=database_spec,
            manifests=manifests,
        )
        
        # extraction paths
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        app_root_path = Path("generated_apps") / thread_id

        file_root_path = os.path.join(app_root_path, current_layer_path)
        os.makedirs(file_root_path, exist_ok=True)

        # save files to filesystem
        for file in result.files:
            with open(os.path.join(file_root_path, file.filename), "w") as f:
                f.write(file.code_content)

        manifest_files = []
        for file in result.files:
            relative_file_path = os.path.join(current_layer_path, file.filename)
            
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
            spec=database_spec.model_dump(),
            manifest_files=manifest_files,
        )
        
        # Update state with results
        return {
            **state,
            "manifests": state.get("manifests", []) + [manifest.model_dump()],
            "next_layer_index": current_layer_index + 1,
        }
