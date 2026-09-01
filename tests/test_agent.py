from agent.evaluator import evaluate_run
from agent.tools import (
    calculator,
    compare_catalog,
    search_catalog,
)


def test_calculator():
    result = calculator("10 * 5 + 2")
    assert result["result"] == 52


def test_catalog_search():
    result = search_catalog("RTX 4060")
    assert result["count"] >= 1


def test_catalog_compare():
    result = compare_catalog(80000)

    assert result["best_match"] is not None
    assert result["best_match"]["price"] <= 80000


def test_evaluator():
    result = evaluate_run(
        task="demo task",
        steps=[
            {"status": "success"},
            {"status": "success"},
        ],
        final_answer="AgentForge completed the task successfully.",
        failures=0,
    )

    assert result["tool_calls"] == 2
    assert result["successful_steps"] == 2
    assert result["failures"] == 0
    assert result["final_score"] > 0