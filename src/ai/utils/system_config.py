system_config = {
    # "intent_interpreter": {
    #     "provider": "ollama",
    #     "model": "gpt-oss:20b",
    #     "additional_kwargs": {},
    # },
    "intent_interpreter": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "additional_kwargs": {
            "reasoning_effort": "low",
        },
    },
    # "architect": {
    #     "provider": "ollama",
    #     "model": "gpt-oss:20b",
    #     "additional_kwargs": {},
    # },
    "architect": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "additional_kwargs": {
            "reasoning_effort": "medium",
        },
    },
    "spec_planner": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "additional_kwargs": {
            "reasoning_effort": "medium",
        },
    },
    "backend_model_agent": {
        "provider": "openai",
        "model": "gpt-5-mini",
        "additional_kwargs": {
            "reasoning_effort": "low",
        },
    }
}