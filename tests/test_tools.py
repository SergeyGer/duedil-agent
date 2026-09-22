import sys
import types

from app.tools import get_search_tool, stringify_search_results


def test_stringify_none():
    assert stringify_search_results(None) == ""


def test_stringify_string_passthrough():
    assert stringify_search_results("hello") == "hello"


def test_stringify_list_of_dicts():
    results = [
        {"title": "Acme", "url": "https://acme.ai", "content": "Acme is a startup"},
        {"title": "Beta", "url": "https://beta.ai", "content": "Beta competitor"},
    ]
    out = stringify_search_results(results)
    assert "Acme" in out
    assert "https://acme.ai" in out
    assert "Beta competitor" in out


def test_stringify_dict_is_wrapped():
    out = stringify_search_results({"title": "Acme", "content": "x"})
    assert "Acme" in out


def test_stringify_other_type():
    assert stringify_search_results(123) == "123"


def test_get_search_tool_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert get_search_tool() is None


def test_get_search_tool_import_failure(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    # A ``None`` entry in sys.modules makes the import raise ImportError.
    monkeypatch.setitem(sys.modules, "langchain_community.tools.tavily_search", None)
    assert get_search_tool() is None


def test_get_search_tool_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

    created: dict = {}

    class FakeTavily:
        def __init__(self, **kwargs):
            created.update(kwargs)

    fake_module = types.ModuleType("langchain_community.tools.tavily_search")
    fake_module.TavilySearchResults = FakeTavily
    monkeypatch.setitem(sys.modules, "langchain_community.tools.tavily_search", fake_module)

    tool = get_search_tool(max_results=3)
    assert isinstance(tool, FakeTavily)
    assert created["max_results"] == 3
    assert created["tavily_api_key"] == "tvly-test"
