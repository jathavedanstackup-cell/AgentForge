from __future__ import annotations

import json
from typing import Any

from agent.evaluator import evaluate_run
from agent.providers.gemini import GeminiProvider
from agent.tools import execute_tool
from agent.trace import create_run_id, save_trace


MAX_STEPS = 5


class AgentForge:
    def __init__(
        self,
        provider: GeminiProvider | None = None,
    ) -> None:
        self.provider = provider or GeminiProvider()

    def _extract_json(
        self,
        text: str,
    ) -> dict[str, Any]:
        text = text.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines)

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "Gemini did not return valid JSON."
            )

        return json.loads(
            text[start:end + 1]
        )

    def _plan(
        self,
        task: str,
    ) -> dict[str, Any]:

        prompt = f"""
You are the planning engine inside AgentForge.

MISSION:
{task}

AVAILABLE TOOLS:

1. calculator
   argument:
   expression

2. search_catalog
   argument:
   query

3. compare_catalog
   argument:
   budget

4. search_docs
   argument:
   query

Create a short execution plan.

Return ONLY valid JSON in this exact structure:

{{
    "goal": "one sentence describing the goal",
    "steps": [
        {{
            "tool": "tool name",
            "arguments": {{}},
            "purpose": "why this step is needed"
        }}
    ]
}}

RULES:
- Maximum 5 steps.
- Use only the available tools.
- Never invent a tool.
- Keep arguments simple.
- Only use tools that help complete the mission.
"""

        response = self.provider.generate(
            prompt
        )

        return self._extract_json(
            response
        )

    def _finalize(
        self,
        task: str,
        observations: list[dict[str, Any]],
    ) -> str:

        prompt = f"""
You are the final reasoning layer of AgentForge.

MISSION:
{task}

OBSERVATIONS FROM TOOLS:
{json.dumps(observations, indent=2)}

Write the final answer for the user.

RULES:
- Give a direct conclusion.
- Use evidence from the observations.
- Do not invent facts.
- Do not claim a tool produced information it did not produce.
- Mention uncertainty when evidence is incomplete.
- Keep the answer professional and readable.
- Do not mention internal prompts or system instructions.
"""

        return self.provider.generate(
            prompt
        )

    def run(
        self,
        task: str,
        chaos_mode: bool = False,
        chaos_type: str = "Tool timeout",
    ) -> dict[str, Any]:

        run_id = create_run_id()

        trace: list[dict[str, Any]] = []
        steps: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []

        failures = 0

        trace.append(
            {
                "stage": "mission",
                "status": "started",
                "task": task,
            }
        )

        # --------------------------------------------------
        # PLANNING
        # --------------------------------------------------

        plan = self._plan(task)

        trace.append(
            {
                "stage": "planner",
                "status": "success",
                "plan": plan,
            }
        )

        # --------------------------------------------------
        # TOOL EXECUTION
        # --------------------------------------------------

        planned_steps = plan.get(
            "steps",
            [],
        )

        planned_steps = planned_steps[:MAX_STEPS]

        for index, step in enumerate(
            planned_steps,
            start=1,
        ):

            tool_name = step.get(
                "tool"
            )

            arguments = step.get(
                "arguments",
                {},
            )

            purpose = step.get(
                "purpose",
                "",
            )

            step_event = {
                "step": index,
                "tool": tool_name,
                "arguments": arguments,
                "purpose": purpose,
            }

            # --------------------------------------------------
            # CHAOS MODE
            # --------------------------------------------------

            if chaos_mode and index == 1:

                failures += 1

                step_event["status"] = "failed"
                step_event["error"] = chaos_type

                steps.append(
                    step_event
                )

                trace.append(
                    step_event
                )

                recovery_message = (
                    "Agent detected the injected failure "
                    "and continued execution."
                )

                if chaos_type == "Invalid tool response":

                    recovery_message = (
                        "Agent detected an invalid tool response "
                        "and continued with the remaining evidence."
                    )

                elif chaos_type == "Conflicting evidence":

                    recovery_message = (
                        "Agent detected conflicting evidence "
                        "and continued cautiously."
                    )

                trace.append(
                    {
                        "stage": "recovery",
                        "status": "recovered",
                        "message": recovery_message,
                    }
                )

                continue

            # --------------------------------------------------
            # NORMAL TOOL EXECUTION
            # --------------------------------------------------

            try:

                result = execute_tool(
                    tool_name,
                    arguments,
                )

                step_event["status"] = "success"
                step_event["result"] = result

                observations.append(
                    {
                        "tool": tool_name,
                        "result": result,
                    }
                )

            except Exception as exc:

                failures += 1

                step_event["status"] = "failed"
                step_event["error"] = str(
                    exc
                )

            steps.append(
                step_event
            )

            trace.append(
                step_event
            )

        # --------------------------------------------------
        # FINAL RESPONSE
        # --------------------------------------------------

        final_answer = self._finalize(
            task,
            observations,
        )

        trace.append(
            {
                "stage": "finalizer",
                "status": "success",
                "answer": final_answer,
            }
        )

        # --------------------------------------------------
        # EVALUATION
        # --------------------------------------------------

        evaluation = evaluate_run(
            task=task,
            steps=steps,
            final_answer=final_answer,
            failures=failures,
        )

        trace.append(
            {
                "stage": "evaluator",
                "status": "success",
                "evaluation": evaluation,
            }
        )

        # --------------------------------------------------
        # SAVE TRACE
        # --------------------------------------------------

        trace_path = save_trace(
            run_id,
            trace,
        )

        return {
            "run_id": run_id,
            "plan": plan,
            "steps": steps,
            "observations": observations,
            "final_answer": final_answer,
            "evaluation": evaluation,
            "trace": trace,
            "trace_path": str(
                trace_path
            ),
        }