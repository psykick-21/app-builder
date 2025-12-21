import json
from tqdm import tqdm
import uuid
from src.ai.graphs import create_orchestrator_graph
from src.ai.graph_states.orchestrator_state import OrchestratorState
import time


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


def run_orchestrator(graph, input_dict: dict, config: dict):
    final_state = None
    for stream_mode, payload in graph.stream(
        input_dict,
        config=config,
        stream_mode=["values", "custom"],
    ):
        if stream_mode == "custom":
            print(payload.get("message"))
        elif stream_mode == "values":
            final_state = payload
        else:
            pass
    
    return final_state

def print_app_location(final_state: dict):
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
    else:
        print("No app location found")

def save_result(final_state: dict):
    result = {
        "prompt": final_state.get("raw_user_input") if final_state else None,
        "user_feedback": final_state.get("user_feedback") if final_state else None,
        "intent": final_state.get("intent") if final_state else None,
        "mode": final_state.get("mode") if final_state else None,
        "change_summary": final_state.get("change_summary") if final_state else None,
        "architecture": final_state.get("architecture") if final_state else None,
        "spec_plan": final_state.get("spec_plan") if final_state else None,
        "existing_intent": final_state.get("existing_intent") if final_state else None,
        "existing_architecture": final_state.get("existing_architecture") if final_state else None,
        "affected_layers": final_state.get("affected_layers") if final_state else None,
        "impact_analysis_changes": final_state.get("impact_analysis_changes") if final_state else None,
    }

    with open("temp/test_data/orchestrator_results.json", "w") as f:
        json.dump([result], f, indent=4, default=str)


if __name__ == "__main__":

    raw_user_input = "Create an expense tracking app. Each expense should have an amount, category, date, and optional notes. I only need this for myself, no login or multi-user support."

    # Generate UUID for thread_id if app_id not provided
    thread_id = str(uuid.uuid4())
    
    initial_state: OrchestratorState = {
        "raw_user_input": raw_user_input
    }

    # Create runnable config with UUID thread_id
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    graph = create_orchestrator_graph()

    final_state = run_orchestrator(graph, initial_state, config)

    save_result(final_state)
    
    print_app_location(final_state)

    while True:
        time.sleep(30)
        user_feedback = input("Enter your feedback (or 'q' to quit): ")
        if user_feedback == 'q':
            break

        if user_feedback:
            final_state = run_orchestrator(
                graph,
                {
                    "user_feedback": user_feedback,
                },
                config
            )
            save_result(final_state)
    
