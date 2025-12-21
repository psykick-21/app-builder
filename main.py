import json
from tqdm import tqdm
from src.ai.graphs import run_orchestrator


# Node name mappings for user-friendly messages
NODE_MESSAGES = {
    "intent_interpreter": "Intent Interpreter node completed",
    "save_intent": "Save intent node completed",
    "architect": "Architect node completed",
    "save_architecture": "Save architecture node completed",
    "spec_planner": "Spec Planner node completed",
    "save_spec_plan": "Save spec plan node completed",
    "code_agents": "Code Agents graph completed",
    "initialize_execution_queue": "Execution queue initialized",
    "backend_model_agent": "Backend model agent completed",
    "database_agent": "Database agent completed",
    "backend_service_agent": "Backend service agent completed",
    "backend_route_agent": "Backend route agent completed",
    "backend_app_agent": "Backend app agent completed",
    "frontend_agent": "Frontend agent completed",
    "finalize": "Finalization completed",
}


if __name__ == "__main__":
    # Load user prompts
    with open("temp/test_data/user_prompts.json", "r") as f:
        user_prompts = json.load(f)

    # Process only the first test use case
    prompt_data = user_prompts[2]
    raw_user_input = prompt_data.get("prompt")
    
    print("="*60)
    print("Running Orchestrator Graph - First Test Use Case")
    print("="*60)
    print(f"\nPrompt: {raw_user_input}\n")
    
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
    result = {
        "prompt": raw_user_input,
        "intent": final_state.get("intent") if final_state else None,
        "mode": final_state.get("mode") if final_state else None,
        "change_summary": final_state.get("change_summary") if final_state else None,
        "architecture": final_state.get("architecture") if final_state else None,
        "spec_plan": final_state.get("spec_plan") if final_state else None,
        "manifests": final_state.get("manifests") if final_state else None,
        "root_dir": str(final_state.get("root_dir")) if final_state and final_state.get("root_dir") else None,
    }
    
    with open("temp/test_data/orchestrator_results.json", "w") as f:
        json.dump([result], f, indent=4, default=str)
    
    # Print summary
    print("\n" + "="*60)
    print("✓ Orchestrator Graph Execution Complete")
    print("="*60)
    print(f"\nResults saved to: temp/test_data/orchestrator_results.json")
    
    if final_state and final_state.get("root_dir"):
        from pathlib import Path
        root_dir = final_state.get("root_dir")
        
        # Convert to absolute path if not already
        if isinstance(root_dir, Path):
            abs_root_dir = root_dir.resolve()
        else:
            abs_root_dir = Path(root_dir).resolve()
        
        print(f"\n📂 App Location: {abs_root_dir}")
        print(f"\n🚀 To run your app, execute these commands:\n")
        print(f"   cd {abs_root_dir}")
        print(f"   ./run.sh")
        print("\n" + "="*60)
    
