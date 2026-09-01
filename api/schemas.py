from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    task: str = Field(
        min_length=10,
        max_length=2000,
    )

    chaos_mode: bool = False

    chaos_type: str = "Tool timeout"


class AgentRunResponse(BaseModel):
    run_id: str

    plan: dict

    steps: list[dict]

    observations: list[dict]

    final_answer: str

    evaluation: dict

    trace: list[dict]

    trace_path: str