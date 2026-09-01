from __future__ import annotations

import ast
import operator
from typing import Any


# ============================================================
# CATALOG
# ============================================================

CATALOG = [
    {
        "name": "VectorBook X1",
        "price": 74999,
        "ram_gb": 16,
        "gpu": "RTX 4050",
        "battery_hours": 7.5,
        "score": 86,
    },
    {
        "name": "ForgeBook Pro",
        "price": 79999,
        "ram_gb": 32,
        "gpu": "RTX 4060",
        "battery_hours": 6.2,
        "score": 92,
    },
    {
        "name": "Nova Air",
        "price": 69999,
        "ram_gb": 16,
        "gpu": "RTX 3050",
        "battery_hours": 9.1,
        "score": 79,
    },
    {
        "name": "CodeStation 14",
        "price": 75999,
        "ram_gb": 24,
        "gpu": "RTX 4050",
        "battery_hours": 8.0,
        "score": 88,
    },
]


# ============================================================
# ENGINEERING DOCUMENTS
# ============================================================

ENGINEERING_DOCS = [
    {
        "title": "API timeout incident",
        "content": (
            "Check upstream latency, connection pools, "
            "retry policy, and timeout configuration."
        ),
    },
    {
        "title": "Memory leak incident",
        "content": (
            "Inspect allocation growth, heap snapshots, "
            "object lifetimes, and long-running workers."
        ),
    },
    {
        "title": "Deployment failure",
        "content": (
            "Inspect build logs, dependency resolution, "
            "environment variables, and startup commands."
        ),
    },
]


# ============================================================
# SAFE CALCULATOR
# ============================================================

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(
    node: ast.AST,
) -> float:

    if isinstance(
        node,
        ast.Constant,
    ):

        if isinstance(
            node.value,
            (int, float),
        ):

            return float(
                node.value
            )

        raise ValueError(
            "Invalid numeric value."
        )


    if isinstance(
        node,
        ast.UnaryOp,
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:

            raise ValueError(
                "Unsupported unary operation."
            )

        return operation(
            _safe_eval(
                node.operand
            )
        )


    if isinstance(
        node,
        ast.BinOp,
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:

            raise ValueError(
                "Unsupported binary operation."
            )

        return operation(
            _safe_eval(
                node.left
            ),
            _safe_eval(
                node.right
            ),
        )


    raise ValueError(
        "Unsupported expression."
    )


def calculator(
    expression: str,
) -> dict[str, Any]:

    expression = expression.strip()

    if not expression:

        raise ValueError(
            "Expression cannot be empty."
        )

    if len(expression) > 100:

        raise ValueError(
            "Expression is too long."
        )

    try:

        tree = ast.parse(
            expression,
            mode="eval",
        )

    except SyntaxError:

        raise ValueError(
            "Invalid mathematical expression."
        )

    result = _safe_eval(
        tree.body
    )

    return {
        "expression": expression,
        "result": result,
    }


# ============================================================
# CATALOG SEARCH
# ============================================================

def search_catalog(
    query: str,
) -> dict[str, Any]:

    query = query.strip()

    if not query:

        raise ValueError(
            "Search query cannot be empty."
        )

    query_lower = query.lower()

    matches: list[dict[str, Any]] = []


    aliases = {
        "laptop": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "laptops": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "notebook": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "notebooks": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "computer": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "computers": [
            "vectorbook",
            "forgebook",
            "nova air",
            "codestation",
        ],
        "ml": [
            "rtx 4050",
            "rtx 4060",
            "rtx 3050",
        ],
        "machine learning": [
            "rtx 4050",
            "rtx 4060",
            "rtx 3050",
        ],
        "gpu": [
            "rtx 4050",
            "rtx 4060",
            "rtx 3050",
        ],
        "graphics": [
            "rtx 4050",
            "rtx 4060",
            "rtx 3050",
        ],
    }


    tokens = [
        token
        for token in query_lower.replace(
            ",",
            " ",
        ).split()
        if len(token) > 1
    ]


    for item in CATALOG:

        name = str(
            item["name"]
        ).lower()

        gpu = str(
            item["gpu"]
        ).lower()

        price = str(
            item["price"]
        )

        ram = str(
            item["ram_gb"]
        )

        battery = str(
            item["battery_hours"]
        )

        score = str(
            item["score"]
        )

        searchable = " ".join(
            [
                name,
                gpu,
                price,
                ram,
                battery,
                score,
            ]
        ).lower()

        matched = False


        # Direct phrase match.

        if query_lower in searchable:

            matched = True


        # Alias match.

        if not matched:

            for alias, products in aliases.items():

                if alias in query_lower:

                    if any(
                        product in searchable
                        for product in products
                    ):

                        matched = True
                        break


        # Token match.

        if not matched and tokens:

            for token in tokens:

                if token in searchable:

                    matched = True
                    break


        if matched:

            matches.append(
                item
            )


    # Budget-aware filtering.

    budget_numbers = []

    cleaned = (
        query_lower
        .replace(
            "₹",
            "",
        )
        .replace(
            ",",
            "",
        )
        .replace(
            "rs",
            "",
        )
        .replace(
            "inr",
            "",
        )
    )

    for token in cleaned.split():

        try:

            value = float(token)

            if value >= 1000:

                budget_numbers.append(
                    value
                )

        except ValueError:

            continue


    if budget_numbers:

        budget = min(
            budget_numbers
        )

        filtered = [
            item
            for item in matches
            if item["price"] <= budget
        ]

        if filtered:

            matches = filtered


    return {
        "query": query,
        "results": matches,
        "count": len(matches),
    }


# ============================================================
# CATALOG COMPARISON
# ============================================================

def compare_catalog(
    budget: float,
) -> dict[str, Any]:

    if budget <= 0:

        raise ValueError(
            "Budget must be greater than zero."
        )

    candidates = [
        item
        for item in CATALOG
        if item["price"] <= budget
    ]

    candidates.sort(
        key=lambda item: (
            item["score"],
            item["ram_gb"],
            item["battery_hours"],
        ),
        reverse=True,
    )

    recommendation = (
        candidates[0]
        if candidates
        else None
    )

    return {
        "budget": budget,
        "candidates": candidates,
        "recommendation": recommendation,
        "count": len(candidates),
    }


# ============================================================
# DOCUMENT SEARCH
# ============================================================

def search_docs(
    query: str,
) -> dict[str, Any]:

    query = query.strip()

    if not query:

        raise ValueError(
            "Documentation query cannot be empty."
        )

    query_lower = query.lower()

    matches = []

    for document in ENGINEERING_DOCS:

        searchable = (
            document["title"]
            + " "
            + document["content"]
        ).lower()

        if (
            query_lower in searchable
            or any(
                token in searchable
                for token in query_lower.split()
                if len(token) > 2
            )
        ):

            matches.append(
                document
            )

    return {
        "query": query,
        "results": matches,
        "count": len(matches),
    }


# ============================================================
# TOOL DISPATCH
# ============================================================

def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:

    tools = {
        "calculator": calculator,
        "search_catalog": search_catalog,
        "compare_catalog": compare_catalog,
        "search_docs": search_docs,
    }

    tool = tools.get(
        tool_name
    )

    if tool is None:

        raise ValueError(
            f"Unknown tool: {tool_name}"
        )

    return tool(
        **arguments
    )