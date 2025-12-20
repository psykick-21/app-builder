"""Architect Agent - translates intent into stable architecture plan."""

from typing import Dict, Any, Optional, List
import json
from dotenv import load_dotenv
import os

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from ..models.architect_models import ArchitectResponse
from ..prompts.architect_prompts import (
    ARCHITECT_INITIAL_PROMPT,
    ARCHITECT_ITERATIVE_PROMPT,
)
from ..graph_states.orchestrator_state import OrchestratorState

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")


class ArchitectAgent:
    """Agent responsible for creating and evolving architecture plans."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        """Initialize the Architect agent.
        
        Args:
            model_name: The OpenAI model to use
            temperature: Temperature for LLM generation (0.0 for deterministic output)
        """
        # self.llm = ChatOllama(
        #     base_url=OLLAMA_BASE_URL,
        #     model="gpt-oss:20b",
        # )
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            reasoning_effort="medium",
        )
        
        # Create LLM with structured output for both modes
        self.llm = self.llm.with_structured_output(ArchitectResponse, method="function_calling")
        
        # Create chains for both modes
        self.initial_chain = ARCHITECT_INITIAL_PROMPT | self.llm
        self.iterative_chain = ARCHITECT_ITERATIVE_PROMPT | self.llm
    
    def execute(
        self,
        intent: Dict[str, Any],
        agent_registry: List[Dict[str, Any]],
        existing_architecture: Optional[Dict[str, Any]] = None
    ) -> ArchitectResponse:
        """Execute the architecture planning logic.
        
        Args:
            intent: Validated intent specification dictionary
            agent_registry: List of available generator agents (system configuration)
            existing_architecture: Existing architecture dictionary (for ITERATIVE mode)
            
        Returns:
            ArchitectResponse from the LLM chain
        """
        # Format agent registry for prompt
        agent_registry_str = json.dumps(agent_registry, indent=2)
        intent_str = json.dumps(intent, indent=2)
        
        if existing_architecture is None:
            # INITIAL mode: create new architecture
            response = self.initial_chain.invoke({
                "intent": intent_str,
                "agent_registry": agent_registry_str,
            })
        else:
            # ITERATIVE mode: evolve existing architecture
            existing_architecture_str = json.dumps(existing_architecture, indent=2)
            response = self.iterative_chain.invoke({
                "intent": intent_str,
                "existing_architecture": existing_architecture_str,
                "agent_registry": agent_registry_str,
            })
        
        # Validate that all generators exist in the registry
        registry_agent_ids = {agent.get("agent_id") for agent in agent_registry}
        for layer in response.execution_layers:
            if layer.generator not in registry_agent_ids:
                raise ValueError(
                    f"Layer '{layer.id}' references generator '{layer.generator}' "
                    f"which is not in the agent registry. "
                    f"Available agents: {registry_agent_ids}"
                )
        
        return response
    
    def __call__(self, state: OrchestratorState, config: Optional[RunnableConfig] = None) -> OrchestratorState:
        """LangGraph node interface.
        
        Args:
            state: Current workflow state containing intent, agent_registry, and optionally existing_architecture
            config: Optional runtime configuration
            
        Returns:
            Updated state with architecture
        """
        # Extract inputs from state
        intent = state.get("intent")
        agent_registry = state.get("agent_registry")
        existing_architecture = state.get("existing_architecture")
        
        if not intent:
            raise ValueError("intent is required in state")
        if not agent_registry:
            raise ValueError("agent_registry is required in state")
        
        # Execute the agent
        response = self.execute(
            intent=intent,
            agent_registry=agent_registry,
            existing_architecture=existing_architecture
        )
        
        # Validate response
        if not isinstance(response, ArchitectResponse):
            raise ValueError(f"Unexpected response type: {type(response)}")
        
        # Update state with results (persistence handled by orchestrator)
        return {
            **state,
            "architecture": response.model_dump(),
        }


if __name__ == "__main__":
    import json
    from tqdm import tqdm
    with open("temp/test_data/intent_interpreter_responses.json", "r") as f:
        intent_interpreter_responses = json.load(f)
    with open("src/ai/utils/agent_registry.json", "r") as f:
        agent_registry = json.load(f)
    architect_agent = ArchitectAgent()
    responses = []
    for response in tqdm(intent_interpreter_responses):
        architect_response = architect_agent.execute(intent=response["intent"], agent_registry=agent_registry)
        responses.append(
            {
                "prompt": response["prompt"],
                "intent": response["intent"],
                "architecture": architect_response.model_dump(),
            }
        )
    with open("temp/test_data/architect_responses.json", "w") as f:
        json.dump(responses, f, indent=4, default=str)
