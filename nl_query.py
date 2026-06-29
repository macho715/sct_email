"""Validated natural-language filter DSL for the HVDC mail app."""

from __future__ import annotations

import json
from typing import Any


ALLOWED_NL_FIELDS = {
    "deliverytime",
    "sendername",
    "senderemail",
    "company_name",
    "site",
    "stage",
    "month",
    "hvdc_cases",
    "subject",
}

ALLOWED_NL_OPS = {"eq", "neq", "ilike", "not_ilike", "in", "gte", "lte", "gt", "lt", "between"}
_COMPARISON_OPS = {"eq": "=", "neq": "!=", "gte": ">=", "lte": "<=", "gt": ">", "lt": "<"}
_MAX_FILTERS = 8
_MAX_LIST_VALUES = 20
_MAX_VALUE_LENGTH = 200


def parse_filter_dsl_response(response_text: str) -> dict[str, Any]:
    """Parse a full Gemini JSON response into a filter DSL object."""
    text = str(response_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object filter DSL")
    return parsed


def _sql_field(field: str) -> str:
    if field not in ALLOWED_NL_FIELDS:
        raise ValueError(f"Unsupported filter field: {field}")
    return f'"{field}"'


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        raise ValueError("Filter value must be a string or number")
    if not isinstance(value, (str, int, float)):
        raise ValueError("Filter value must be a string or number")
    if isinstance(value, str) and len(value) > _MAX_VALUE_LENGTH:
        raise ValueError("Filter value is too long")
    return value


def build_where_from_filter_dsl(dsl: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build a parameterized WHERE fragment from a constrained JSON DSL."""
    if not isinstance(dsl, dict) or "where" in dsl or "sql" in dsl:
        raise ValueError("Expected filter DSL object, not SQL")

    filters = dsl.get("filters", [])
    if not isinstance(filters, list) or len(filters) > _MAX_FILTERS:
        raise ValueError("Invalid filter list")
    if not filters:
        return "", []

    logic = str(dsl.get("logic", "and")).lower()
    if logic not in {"and", "or"}:
        raise ValueError("Invalid filter logic")
    joiner = f" {logic.upper()} "

    clauses: list[str] = []
    params: list[Any] = []

    for item in filters:
        if not isinstance(item, dict):
            raise ValueError("Invalid filter item")

        field = str(item.get("field", "")).strip()
        op = str(item.get("op", "")).strip().lower()
        value = item.get("value")

        if op not in ALLOWED_NL_OPS:
            raise ValueError(f"Unsupported filter op: {op}")
        column = _sql_field(field)

        if op in {"ilike", "not_ilike"}:
            text = str(_scalar(value))
            clauses.append(f"CAST({column} AS VARCHAR) {'NOT ' if op == 'not_ilike' else ''}ILIKE ?")
            params.append(f"%{text}%")
        elif op == "in":
            if not isinstance(value, list) or not value or len(value) > _MAX_LIST_VALUES:
                raise ValueError("IN filter requires a bounded non-empty value list")
            values = [_scalar(v) for v in value]
            placeholders = ", ".join(["?"] * len(values))
            clauses.append(f"{column} IN ({placeholders})")
            params.extend(values)
        elif op == "between":
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("BETWEEN filter requires exactly two values")
            start, end = _scalar(value[0]), _scalar(value[1])
            clauses.append(f"{column} BETWEEN ? AND ?")
            params.extend([start, end])
        else:
            clauses.append(f"{column} {_COMPARISON_OPS[op]} ?")
            params.append(_scalar(value))

    return "(" + joiner.join(clauses) + ")", params
