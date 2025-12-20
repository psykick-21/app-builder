"""Intent Interpreter Agent - translates natural language into structured intent."""

from typing import Dict, Any, Optional
import json
from dotenv import load_dotenv
import os

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from ..models.intent_models import IntentInterpreterResponse
from ..prompts.intent_interpreter_prompts import (
    INTENT_INTERPRETER_CREATE_PROMPT,
    INTENT_INTERPRETER_MODIFY_PROMPT,
)
from ..graph_states.intent_interpreter_state import IntentInterpreterState

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

class IntentInterpreterAgent:
    """Agent responsible for creating and evolving structured intent specifications."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        """Initialize the Intent Interpreter agent.
        
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
            reasoning_effort="low",
        )
        
        # Create LLM with structured output for both modes
        self.llm = self.llm.with_structured_output(IntentInterpreterResponse, method="function_calling")
        
        # Create chains for both modes
        self.create_chain = INTENT_INTERPRETER_CREATE_PROMPT | self.llm
        self.modify_chain = INTENT_INTERPRETER_MODIFY_PROMPT | self.llm
    
    def execute(self, raw_user_input: str = None, existing_intent: Dict[str, Any] = None, user_feedback: str = None) -> IntentInterpreterResponse:
        """Execute the intent interpretation logic.
        
        Args:
            raw_user_input: User's application description (for CREATE mode)
            existing_intent: Existing intent dictionary (for MODIFY mode)
            user_feedback: User feedback for modifying intent (for MODIFY mode)
            
        Returns:
            Raw IntentInterpreterResponse from the LLM chain
        """
        if existing_intent is None:
            # CREATE mode: extract intent from raw user input
            if not raw_user_input:
                raise ValueError("raw_user_input is required for CREATE mode")
            
            response = self.create_chain.invoke({
                "raw_user_input": raw_user_input,
            })
        else:
            # MODIFY mode: evolve existing intent based on feedback
            if not user_feedback:
                raise ValueError("user_feedback is required for MODIFY mode")
            
            response = self.modify_chain.invoke({
                "existing_intent": json.dumps(existing_intent, indent=2),
                "user_feedback": user_feedback,
            })

        response_dict = response.model_dump()

        # Convert intent model to dict
        intent_dict = response_dict["intent"]
        
        # Ensure default assumptions are always included
        DEFAULT_ASSUMPTIONS = ["Single-user application", "Local execution"]
        existing_assumptions = intent_dict.get("assumptions", [])
        
        # Merge defaults with existing assumptions, ensuring defaults are always present
        merged_assumptions = list(existing_assumptions) if existing_assumptions else []
        for default_assumption in DEFAULT_ASSUMPTIONS:
            if default_assumption not in merged_assumptions:
                merged_assumptions.insert(0, default_assumption)  # Insert at beginning
        
        intent_dict["assumptions"] = merged_assumptions
        
        return IntentInterpreterResponse(**response_dict)
    
    def __call__(self, state: IntentInterpreterState, config: Optional[RunnableConfig] = None) -> IntentInterpreterState:
        """LangGraph node interface.
        
        Args:
            state: Current workflow state
            config: Optional runtime configuration
            
        Returns:
            Updated state with intent, mode, and change_summary
        """
        # Extract inputs from state
        raw_user_input = state.get("raw_user_input")
        existing_intent = state.get("existing_intent")
        user_feedback = state.get("user_feedback")
        
        # Execute the agent
        response = self.execute(
            raw_user_input=raw_user_input,
            existing_intent=existing_intent,
            user_feedback=user_feedback
        )
        
        # Validate response
        if not isinstance(response, IntentInterpreterResponse):
            raise ValueError(f"Unexpected response type: {type(response)}")
        
        
        # Update state with results (persistence handled by orchestrator)
        return {
            **state,
            "intent": response.intent.model_dump(),
            "mode": response.mode,
            "change_summary": response.change_summary,
        }


if __name__ == "__main__":
    import json
    from tqdm import tqdm
    with open("temp/test_data/user_prompts.json", "r") as f:
        user_prompts = json.load(f)
    agent = IntentInterpreterAgent()
    responses = []
    for prompt in tqdm(user_prompts):
        response = agent.execute(raw_user_input=prompt["prompt"])
        responses.append({"prompt": prompt["prompt"], **response.model_dump()})
    with open("temp/test_data/intent_interpreter_responses.json", "w") as f:
        json.dump(responses, f, indent=4)