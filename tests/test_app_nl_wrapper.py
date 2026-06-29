import ast
import sys
import types
from pathlib import Path

from nl_query import ALLOWED_NL_FIELDS, build_where_from_filter_dsl, parse_filter_dsl_response


def _load_nl_to_sql_from_app():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app.py")
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_nl_to_sql"
    )
    module = ast.Module(body=[function], type_ignores=[])
    code = compile(ast.fix_missing_locations(module), "app.py", "exec")
    namespace = {
        "ALLOWED_NL_FIELDS": ALLOWED_NL_FIELDS,
        "build_where_from_filter_dsl": build_where_from_filter_dsl,
        "parse_filter_dsl_response": parse_filter_dsl_response,
    }
    exec(code, namespace)
    return namespace["_nl_to_sql"]


def _install_fake_genai(monkeypatch, response_text: str):
    class _FakeResponse:
        text = response_text

    class _FakeModels:
        def generate_content(self, **_kwargs):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = _FakeModels()

    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = _FakeClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def test_nl_to_sql_wrapper_accepts_nested_filter_dsl(monkeypatch):
    _install_fake_genai(
        monkeypatch,
        '{"logic":"and","filters":[{"field":"sendername","op":"ilike","value":"Mammoet"}]}',
    )
    nl_to_sql = _load_nl_to_sql_from_app()

    where, params = nl_to_sql("Mammoet emails", "fake-key")

    assert where == '(CAST("sendername" AS VARCHAR) ILIKE ?)'
    assert params == ["%Mammoet%"]


def test_nl_to_sql_wrapper_rejects_raw_sql_response(monkeypatch):
    _install_fake_genai(
        monkeypatch,
        '{"where":"sendername ILIKE ?","params":["%Mammoet%"]}',
    )
    nl_to_sql = _load_nl_to_sql_from_app()

    assert nl_to_sql("Mammoet emails", "fake-key") == ("", [])
