from __future__ import annotations


def evaluate_run(
    task: str,
    steps: list[dict],
    final_answer: str,
    failures: int,
) -> dict:
    total_steps = len(steps)

    successful_steps = sum(
        1
        for step in steps
        if step.get("status") == "success"
    )

    if total_steps == 0:
        task_completion = 0
    else:
        task_completion = round(
            (
                successful_steps
                / total_steps
            )
            * 100
        )

    if failures == 0:
        recovery = 100
    else:
        recovery = max(
            0,
            100 - (failures * 30),
        )

    tool_score = min(
        total_steps * 20,
        100,
    )

    answer_score = min(
        max(
            len(final_answer.strip()) * 2,
            0,
        ),
        100,
    )

    final_score = round(
        (
            task_completion * 0.40
            + recovery * 0.20
            + tool_score * 0.15
            + answer_score * 0.25
        ),
        1,
    )

    return {
        "task": task,
        "task_completion": task_completion,
        "recovery": recovery,
        "tool_calls": total_steps,
        "successful_steps": successful_steps,
        "failures": failures,
        "answer_quality": answer_score,
        "final_score": final_score,
    }