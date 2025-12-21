"""Architect Agent - translates intent into stable architecture plan."""

from typing import Dict, Any, Optional, List, Literal
import json
from dotenv import load_dotenv
import os

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langgraph.config import get_stream_writer

from ..models.architect_models import ArchitectResponse
from ..prompts.architect_prompts import (
    ARCHITECT_INITIAL_PROMPT,
    ARCHITECT_ITERATIVE_PROMPT,
)
from ..graph_states.orchestrator_state import OrchestratorState

from ..utils.llm_provider import init_llm

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")


class ArchitectAgent:
    """Agent responsible for creating and evolving architecture plans."""
    
    def __init__(
        self, 
        provider: Literal["openai", "ollama"],
        model: str, 
        additional_kwargs: dict,
    ):
        """Initialize the Architect agent.
        
        Args:
            provider: The provider to use
            model: The model to use
            additional_kwargs: Additional kwargs to pass to the LLM
        """
        self.llm = init_llm(provider, model, additional_kwargs)
        
        # Create LLM with structured output for both modes
        self.llm = self.llm.with_structured_output(ArchitectResponse, method="function_calling")
        
        # Create chains for both modes
        self.initial_chain = ARCHITECT_INITIAL_PROMPT | self.llm
        self.iterative_chain = ARCHITECT_ITERATIVE_PROMPT | self.llm
    
    def execute(
        self,
        intent: Dict[str, Any],
        agent_registry: List[Dict[str, Any]],
        mode: Literal["CREATE", "MODIFY"],
        existing_architecture: Optional[Dict[str, Any]] = None
    ) -> ArchitectResponse:
        """Execute the architecture planning logic.
        
        Args:
            intent: Validated intent specification dictionary
            agent_registry: List of available generator agents (system configuration)
            mode: Mode of the architecture planning (CREATE or MODIFY)
            existing_architecture: Existing architecture dictionary (for ITERATIVE mode)
            
        Returns:
            ArchitectResponse from the LLM chain
        """
        # Format agent registry for prompt
        agent_registry_str = json.dumps(agent_registry, indent=2)
        intent_str = json.dumps(intent, indent=2)
        
        if mode == "CREATE":
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
        # Get stream writer for custom streaming
        writer = get_stream_writer()
        
        # Extract inputs from state
        intent = state.get("intent")
        agent_registry = state.get("agent_registry")
        existing_architecture = state.get("existing_architecture")
        mode = state.get("mode")
        
        if not intent:
            raise ValueError("intent is required in state")
        if not agent_registry:
            raise ValueError("agent_registry is required in state")
        
        # Send custom message before execution
        if writer:
            writer({
                "message": f"🏗️ Planning architecture ({mode} mode)...",
                "node": "architect",
                "status": "starting"
            })
        
        # Execute the agent
        response = self.execute(
            intent=intent,
            agent_registry=agent_registry,
            existing_architecture=existing_architecture,
            mode=mode
        )
        
        # Validate response
        if not isinstance(response, ArchitectResponse):
            raise ValueError(f"Unexpected response type: {type(response)}")
        
        # Send custom message after execution
        if writer:
            writer({
                "message": f"✅ Architecture planning completed ({mode} mode).",
                "node": "architect",
                "status": "completed",
            })
        
        # Update state with results (persistence handled by orchestrator)
        return {
            **state,
            "architecture": response.model_dump(),
        }
