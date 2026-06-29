import pytest

from nl_query import build_where_from_filter_dsl, parse_filter_dsl_response


def test_parse_filter_dsl_response_parses_complete_nested_json():
    parsed = parse_filter_dsl_response(
        '{"logic":"and","filters":[{"field":"sendername","op":"ilike","value":"Mammoet"}]}'
    )

    assert parsed == {
        "logic": "and",
        "filters": [{"field": "sendername", "op": "ilike", "value": "Mammoet"}],
    }


def test_parse_filter_dsl_response_rejects_json_with_extra_text():
    with pytest.raises(ValueError):
        parse_filter_dsl_response(
            'Here is JSON: {"filters":[{"field":"sendername","op":"ilike","value":"Mammoet"}]}'
        )


def test_build_where_from_filter_dsl_creates_parameterized_ilike():
    where, params = build_where_from_filter_dsl(
        {"filters": [{"field": "sendername", "op": "ilike", "value": "Mammoet"}]}
    )

    assert where == '(CAST("sendername" AS VARCHAR) ILIKE ?)'
    assert params == ["%Mammoet%"]


def test_build_where_from_filter_dsl_rejects_raw_sql_shape():
    with pytest.raises(ValueError, match="not SQL"):
        build_where_from_filter_dsl({"where": "sendername ILIKE ?", "params": ["%Mammoet%"]})


def test_build_where_from_filter_dsl_rejects_unknown_field():
    with pytest.raises(ValueError, match="Unsupported filter field"):
        build_where_from_filter_dsl(
            {"filters": [{"field": "plaintextbody", "op": "ilike", "value": "claim"}]}
        )


def test_build_where_from_filter_dsl_supports_between_and_in():
    where, params = build_where_from_filter_dsl(
        {
            "logic": "and",
            "filters": [
                {"field": "deliverytime", "op": "between", "value": ["2025-03-01", "2025-03-31"]},
                {"field": "stage", "op": "in", "value": ["MRR", "MIR"]},
            ],
        }
    )

    assert where == '("deliverytime" BETWEEN ? AND ? AND "stage" IN (?, ?))'
    assert params == ["2025-03-01", "2025-03-31", "MRR", "MIR"]
