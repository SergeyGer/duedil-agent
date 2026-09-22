import sys
import types

from app.tools import get_search_tool, stringify_search_results


def _fake_module(name: str, **attrs) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


# --- stringify_search_results ---------------------------------------------
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


def test_stringify_dict_with_results_list():
    payload = {
        "query": "acme",
        "results": [{"title": "Acme", "url": "https://acme.ai", "content": "Acme is a startup"}],
    }
    out = stringify_search_results(payload)
    assert "Acme is a startup" in out
    assert "https://acme.ai" in out


def test_stringify_plain_dict_is_wrapped():
    out = stringify_search_results({"title": "Acme", "content": "x"})
    assert "Acme" in out


def test_stringify_other_type():
    assert stringify_search_results(123) == "123"


# --- get_search_tool -------------------------------------------------------
def test_get_search_tool_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert get_search_tool() is None


def test_get_search_tool_prefers_langchain_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    created: dict = {}

    class FakeTavilySearch:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "langchain_tavily",
        _fake_module("langchain_tavily", TavilySearch=FakeTavilySearch),
    )

    tool = get_search_tool(max_results=3)
    assert isinstance(tool, FakeTavilySearch)
    assert created == {"max_results": 3, "tavily_api_key": "tvly-test"}


def test_get_search_tool_falls_back_to_community(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setitem(sys.modules, "langchain_tavily", None)  # forces ImportError
    created: dict = {}

    class FakeTavilySearchResults:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "langchain_community.tools.tavily_search",
        _fake_module(
            "langchain_community.tools.tavily_search",
            TavilySearchResults=FakeTavilySearchResults,
        ),
    )

    tool = get_search_tool(max_results=2)
    assert isinstance(tool, FakeTavilySearchResults)
    assert created["max_results"] == 2


def test_get_search_tool_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setitem(sys.modules, "langchain_tavily", None)
    monkeypatch.setitem(sys.modules, "langchain_community.tools.tavily_search", None)
    assert get_search_tool() is None
