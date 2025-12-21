import json
from tqdm import tqdm
from src.ai.graphs import run_code_agents


# Node name mappings for user-friendly messages
NODE_MESSAGES = {
    "initialize_execution_queue": "Execution queue initialized",
    "backend_model_agent": "Backend model agent completed",
    "backend_service_agent": "Backend service agent completed",
    "backend_route_agent": "Backend route agent completed",
    "frontend_agent": "Frontend agent completed",
    "database_agent": "Database agent completed",
    "backend_app_agent": "Backend app agent completed",
}


if __name__ == "__main__":
    # Load spec planner responses (which contain intent, architecture, and specs)
    with open("temp/test_data/spec_planner_responses.json", "r") as f:
        spec_planner_responses = json.load(f)

    # Process each response through the code agents graph
    results = []
    for response_data in tqdm(spec_planner_responses, desc="Processing code generation"):
        intent = response_data.get("intent")
        architecture = response_data.get("architecture")
        spec_responses = response_data.get("spec_responses", [])
        app_id = response_data.get("app_id")  # If available
        
        if not intent or not architecture:
            print(f"  ⚠ Skipping: missing intent or architecture")
            continue
        
        # Convert spec_responses to the format expected by code agents
        specs = spec_responses if spec_responses else None
        
        # Run the code agents graph and iterate through events
        final_state = None
        for event in run_code_agents(
            intent=intent,
            architecture=architecture,
            specs=specs,
            app_id=app_id,
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
                "intent": intent,
                "architecture": architecture,
                "manifests": final_state.get("manifests"),
                "execution_queue": final_state.get("execution_queue"),
            })
    
    with open("temp/test_data/code_agents_results.json", "w") as f:
        json.dump(results, f, indent=4, default=str)
    
    # Print summary
    print(f"\nProcessed {len(results)} code generation tasks")
    print(f"Results saved to: temp/test_data/code_agents_results.json")
