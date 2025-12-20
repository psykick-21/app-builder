import json
from tqdm import tqdm
from src.ai.graphs import run_orchestrator


# Node name mappings for user-friendly messages
NODE_MESSAGES = {
    "intent_interpreter": "Intent Interpreter node completed",
    "save_intent": "Save intent node completed",
    "architect": "Architect node completed",
    "save_architecture": "Save architecture node completed",
}


if __name__ == "__main__":
    # Load user prompts
    with open("temp/test_data/user_prompts.json", "r") as f:
        user_prompts = json.load(f)

    # Process each prompt through the orchestrator graph
    results = []
    for prompt_data in tqdm(user_prompts, desc="Processing prompts"):
        raw_user_input = prompt_data.get("prompt")
        
        # Run the orchestrator graph and iterate through events
        final_state = None
        for event in run_orchestrator(
            raw_user_input=raw_user_input,
            agent_registry=None,  # Will be loaded automatically
            app_id=None,  # Will generate UUID automatically
        ):
            node_name = event.get("node")
            state = event.get("state")
            
            # Print node completion message
            if node_name in NODE_MESSAGES:
                print(f"  ✓ {NODE_MESSAGES[node_name]}")
            
            # Store the state from each event (last one will be final)
            if state is not None:
                final_state = state
        
        # Collect results
        if final_state:
            results.append({
                "prompt": raw_user_input,
                "intent": final_state.get("intent"),
                "mode": final_state.get("mode"),
                "change_summary": final_state.get("change_summary"),
                "architecture": final_state.get("architecture"),
            })
    
    with open("temp/test_data/orchestrator_results.json", "w") as f:
        json.dump(results, f, indent=4, default=str)
    
    # Print summary
    print(f"\nProcessed {len(results)} prompts")
    print(f"Files saved to: generated_apps/<uuid>/spec/")
    
