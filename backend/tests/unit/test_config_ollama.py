from src import config
from src.config import Config


def test_default_ollama_base_url_uses_localhost_outside_docker(monkeypatch):
    monkeypatch.setattr(config.os.path, "exists", lambda path: False)

    assert Config._default_ollama_base_url() == "http://localhost:11434/v1"


def test_default_ollama_base_url_uses_host_gateway_in_docker(monkeypatch):
    monkeypatch.setattr(config.os.path, "exists", lambda path: path == "/.dockerenv")

    assert Config._default_ollama_base_url() == "http://host.docker.internal:11434/v1"

def test_infer_llm_fallbacks_uses_other_configured_provider_keys():
    runtime_config = Config.__new__(Config)
    runtime_config.google_api_key = "google-key"
    runtime_config.openai_api_key = "openai-key"
    runtime_config.anthropic_api_key = "anthropic-key"

    assert runtime_config._infer_llm_fallbacks("google-gla:gemini-3-flash-preview") == [
        "openai:gpt-5.2",
        "anthropic:claude-4-sonnet",
    ]
