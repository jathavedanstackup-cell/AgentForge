from fastapi import FastAPI, HTTPException

from agent.core import AgentForge
from api.schemas import (
    AgentRunRequest,
    AgentRunResponse,
)


app = FastAPI(
    title="AgentForge",
    description=(
        "AI Agent Laboratory for building, "
        "running, observing, breaking, "
        "and evaluating AI agents."
    ),
    version="1.0.0",
)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "AgentForge",
    }


@app.post(
    "/api/v1/run",
    response_model=AgentRunResponse,
)
def run_agent(
    request: AgentRunRequest,
) -> AgentRunResponse:

    try:

        agent = AgentForge()

        result = agent.run(
            task=request.task,
            chaos_mode=request.chaos_mode,
            chaos_type=request.chaos_type,
        )

        return AgentRunResponse(
            **result
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc