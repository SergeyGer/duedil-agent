from app.config import get_llm, get_model_name


def test_get_model_name_default(monkeypatch):
    monkeypatch.delenv("DUE_DIL_MODEL", raising=False)
    assert get_model_name() == "gpt-4o"


def test_get_model_name_override(monkeypatch):
    monkeypatch.setenv("DUE_DIL_MODEL", "claude-3-5-sonnet")
    assert get_model_name() == "claude-3-5-sonnet"


def test_get_llm_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from langchain_openai import ChatOpenAI

    assert isinstance(get_llm(model="gpt-4o"), ChatOpenAI)


def test_get_llm_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from langchain_anthropic import ChatAnthropic

    assert isinstance(get_llm(model="claude-3-5-sonnet"), ChatAnthropic)
