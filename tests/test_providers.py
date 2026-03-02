"""Tests for BSS provider abstraction — base class, GGUF, OpenAI-compat, registry."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from integrations.providers import Provider, get_provider


# ── Provider base class ──────────────────────────────────────


class TestProviderInterface:
    def test_provider_is_abstract(self):
        """Cannot instantiate Provider directly."""
        with pytest.raises(TypeError):
            Provider()

    def test_provider_has_required_methods(self):
        """Provider ABC defines load, unload, is_loaded, infer, chat."""
        required = {"load", "unload", "is_loaded", "infer", "chat"}
        abstract = set(Provider.__abstractmethods__)
        assert required == abstract


# ── get_provider registry ────────────────────────────────────


class TestGetProvider:
    def test_get_gguf_provider(self):
        provider = get_provider("gguf")
        assert isinstance(provider, Provider)
        assert type(provider).__name__ == "GGUFProvider"

    def test_get_openai_provider(self):
        provider = get_provider("openai")
        assert isinstance(provider, Provider)
        assert type(provider).__name__ == "OpenAIProvider"

    def test_get_anthropic_provider(self):
        provider = get_provider("anthropic")
        assert isinstance(provider, Provider)
        assert type(provider).__name__ == "AnthropicProvider"

    def test_get_gemini_provider(self):
        provider = get_provider("gemini")
        assert isinstance(provider, Provider)
        assert type(provider).__name__ == "GeminiProvider"

    def test_get_huggingface_provider(self):
        provider = get_provider("huggingface")
        assert isinstance(provider, Provider)
        assert type(provider).__name__ == "HuggingFaceProvider"

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            get_provider("nonexistent")


# ── GGUFProvider ─────────────────────────────────────────────


class TestGGUFProvider:
    def test_initial_state(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()
        assert not p.is_loaded()

    @patch("integrations.providers.gguf.Llama", create=True)
    def test_load_success(self, MockLlama, tmp_path):
        """Load succeeds when file exists and Llama initializes."""
        from integrations.providers.gguf import GGUFProvider

        # Create a dummy file
        gguf_file = tmp_path / "model.gguf"
        gguf_file.touch()

        # Patch the import inside the module
        with patch.dict("sys.modules", {"llama_cpp": MagicMock(Llama=MockLlama)}):
            p = GGUFProvider()
            result = p.load({"path": str(gguf_file), "n_ctx": 2048, "threads": 2})

        assert result is True
        assert p.is_loaded()

    def test_load_missing_file(self, tmp_path):
        """Load fails when file doesn't exist."""
        from integrations.providers.gguf import GGUFProvider

        mock_llama = MagicMock()
        with patch.dict("sys.modules", {"llama_cpp": mock_llama}):
            p = GGUFProvider()
            result = p.load({"path": str(tmp_path / "nonexistent.gguf")})

        assert result is False
        assert not p.is_loaded()

    def test_unload(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()
        p._model = MagicMock()
        assert p.is_loaded()

        p.unload()
        assert not p.is_loaded()

    def test_infer_delegates_to_llama(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"completion_tokens": 5},
        }
        p._model = mock_model

        response, tokens, elapsed = p.infer(
            "You are helpful.", "Say hi",
            {"max_tokens": 100, "system_suffix": " /no_think"},
        )

        assert response == "Hello world"
        assert tokens == 5
        assert elapsed >= 0
        mock_model.create_chat_completion.assert_called_once()

        # Verify system_suffix is appended when configured
        call_args = mock_model.create_chat_completion.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        assert messages[0]["content"].endswith("/no_think")

    def test_infer_no_suffix_by_default(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {"completion_tokens": 1},
        }
        p._model = mock_model

        p.infer("You are helpful.", "Say hi", {"max_tokens": 100})

        call_args = mock_model.create_chat_completion.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        assert messages[0]["content"] == "You are helpful."

    def test_chat_delegates_to_llama(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Continuing chat"}}],
            "usage": {"completion_tokens": 3},
        }
        p._model = mock_model

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        response, tokens, elapsed = p.chat("System", history, "How are you?", {"max_tokens": 100})

        assert response == "Continuing chat"
        assert tokens == 3

        # Verify messages include history
        call_args = mock_model.create_chat_completion.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        assert len(messages) == 4  # system + 2 history + user

    def test_infer_error_handling(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()

        mock_model = MagicMock()
        mock_model.create_chat_completion.side_effect = RuntimeError("GPU OOM")
        p._model = mock_model

        response, tokens, elapsed = p.infer("System", "User", {})

        assert "[inference error:" in response
        assert "GPU OOM" in response
        assert tokens == 0

    def test_chat_error_handling(self):
        from integrations.providers.gguf import GGUFProvider
        p = GGUFProvider()

        mock_model = MagicMock()
        mock_model.create_chat_completion.side_effect = RuntimeError("timeout")
        p._model = mock_model

        response, tokens, elapsed = p.chat("System", [], "User", {})

        assert "[chat error:" in response
        assert tokens == 0


# ── AnthropicProvider ────────────────────────────────────────


class TestAnthropicProvider:
    def test_initial_state(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()
        assert not p.is_loaded()

    def test_load_success(self):
        from integrations.providers.anthropic import AnthropicProvider

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicProvider()
            result = p.load({"api_key": "sk-ant-test", "model": "claude-sonnet-4-20250514"})

        assert result is True
        assert p.is_loaded()
        assert p._model == "claude-sonnet-4-20250514"

    def test_load_from_env_var(self):
        from integrations.providers.anthropic import AnthropicProvider

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-env"}):
                p = AnthropicProvider()
                result = p.load({"model": "claude-sonnet-4-20250514"})

        assert result is True
        assert p.is_loaded()

    def test_load_no_key_fails(self):
        from integrations.providers.anthropic import AnthropicProvider

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with patch.dict(os.environ, {}, clear=True):
                p = AnthropicProvider()
                result = p.load({"model": "claude-sonnet-4-20250514"})

        assert result is False
        assert not p.is_loaded()

    def test_unload(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()
        p._client = MagicMock()
        p._model = "test"
        assert p.is_loaded()

        p.unload()
        assert not p.is_loaded()
        assert p._client is None
        assert p._model is None

    def test_infer_delegates_to_client(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello from Claude")]
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response
        p._client = mock_client
        p._model = "claude-sonnet-4-20250514"

        response, tokens, elapsed = p.infer("You are helpful.", "Say hi", {"max_tokens": 100})

        assert response == "Hello from Claude"
        assert tokens == 5
        assert elapsed >= 0
        mock_client.messages.create.assert_called_once()

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."
        assert call_kwargs["messages"] == [{"role": "user", "content": "Say hi"}]

    def test_chat_includes_history(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Continuing chat")]
        mock_response.usage.output_tokens = 3
        mock_client.messages.create.return_value = mock_response
        p._client = mock_client
        p._model = "claude-sonnet-4-20250514"

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        response, tokens, elapsed = p.chat("System", history, "How are you?", {"max_tokens": 100})

        assert response == "Continuing chat"
        assert tokens == 3

        call_kwargs = mock_client.messages.create.call_args[1]
        assert len(call_kwargs["messages"]) == 3  # 2 history + user
        assert call_kwargs["system"] == "System"

    def test_infer_error_handling(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")
        p._client = mock_client
        p._model = "test"

        response, tokens, elapsed = p.infer("System", "User", {})

        assert "[inference error:" in response
        assert "API error" in response
        assert tokens == 0

    def test_chat_error_handling(self):
        from integrations.providers.anthropic import AnthropicProvider
        p = AnthropicProvider()

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("timeout")
        p._client = mock_client
        p._model = "test"

        response, tokens, elapsed = p.chat("System", [], "User", {})

        assert "[chat error:" in response
        assert tokens == 0

    def test_default_model(self):
        from integrations.providers.anthropic import AnthropicProvider

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            p = AnthropicProvider()
            p.load({"api_key": "sk-ant-test"})

        assert p._model == "claude-sonnet-4-20250514"


# ── GeminiProvider ──────────────────────────────────────────


class TestGeminiProvider:
    def test_initial_state(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()
        assert not p.is_loaded()

    def test_load_success(self):
        from integrations.providers.gemini import GeminiProvider

        mock_genai = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            p = GeminiProvider()
            result = p.load({"api_key": "AIza-test", "model": "gemini-2.0-flash"})

        assert result is True
        assert p.is_loaded()
        assert p._model == "gemini-2.0-flash"

    def test_load_from_env_var(self):
        from integrations.providers.gemini import GeminiProvider

        mock_genai = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza-env"}):
                p = GeminiProvider()
                result = p.load({"model": "gemini-2.0-flash"})

        assert result is True

    def test_load_from_gemini_env_var(self):
        from integrations.providers.gemini import GeminiProvider

        mock_genai = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-gemini"}, clear=True):
                p = GeminiProvider()
                result = p.load({"model": "gemini-2.0-flash"})

        assert result is True

    def test_load_no_key_fails(self):
        from integrations.providers.gemini import GeminiProvider

        mock_genai = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {}, clear=True):
                p = GeminiProvider()
                result = p.load({"model": "gemini-2.0-flash"})

        assert result is False

    def test_unload(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()
        p._client = MagicMock()
        p._model = "test"
        assert p.is_loaded()

        p.unload()
        assert not p.is_loaded()

    def test_infer_delegates_to_client(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini"
        mock_response.usage_metadata.candidates_token_count = 5
        mock_client.models.generate_content.return_value = mock_response
        p._client = mock_client
        p._model = "gemini-2.0-flash"

        mock_types = MagicMock()
        with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google.genai.types": mock_types}):
            response, tokens, elapsed = p.infer("You are helpful.", "Say hi", {"max_tokens": 100})

        assert response == "Hello from Gemini"
        assert tokens == 5
        mock_client.models.generate_content.assert_called_once()

    def test_chat_maps_roles(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Chat response"
        mock_response.usage_metadata.candidates_token_count = 3
        mock_client.models.generate_content.return_value = mock_response
        p._client = mock_client
        p._model = "gemini-2.0-flash"

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        mock_types = MagicMock()
        with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google.genai.types": mock_types}):
            response, tokens, elapsed = p.chat("System", history, "How are you?", {})

        assert response == "Chat response"
        assert tokens == 3

    def test_infer_error_handling(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")
        p._client = mock_client
        p._model = "test"

        mock_types = MagicMock()
        with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google.genai.types": mock_types}):
            response, tokens, elapsed = p.infer("System", "User", {})

        assert "[inference error:" in response
        assert tokens == 0

    def test_chat_error_handling(self):
        from integrations.providers.gemini import GeminiProvider
        p = GeminiProvider()

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("timeout")
        p._client = mock_client
        p._model = "test"

        mock_types = MagicMock()
        with patch.dict("sys.modules", {"google.genai": MagicMock(types=mock_types), "google.genai.types": mock_types}):
            response, tokens, elapsed = p.chat("System", [], "User", {})

        assert "[chat error:" in response
        assert tokens == 0

    def test_default_model(self):
        from integrations.providers.gemini import GeminiProvider

        mock_genai = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            p = GeminiProvider()
            p.load({"api_key": "AIza-test"})

        assert p._model == "gemini-2.0-flash"


# ── HuggingFaceProvider ─────────────────────────────────────


class TestHuggingFaceProvider:
    def test_initial_state(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()
        assert not p.is_loaded()

    def test_load_success(self):
        from integrations.providers.huggingface import HuggingFaceProvider

        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            p = HuggingFaceProvider()
            result = p.load({"api_key": "hf_test", "model": "mistralai/Mistral-7B-Instruct-v0.3"})

        assert result is True
        assert p.is_loaded()
        assert p._model == "mistralai/Mistral-7B-Instruct-v0.3"

    def test_load_from_hf_token(self):
        from integrations.providers.huggingface import HuggingFaceProvider

        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            with patch.dict(os.environ, {"HF_TOKEN": "hf_env"}):
                p = HuggingFaceProvider()
                result = p.load({"model": "test/model"})

        assert result is True

    def test_load_from_hugging_face_hub_token(self):
        from integrations.providers.huggingface import HuggingFaceProvider

        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            with patch.dict(os.environ, {"HUGGING_FACE_HUB_TOKEN": "hf_hub"}, clear=True):
                p = HuggingFaceProvider()
                result = p.load({"model": "test/model"})

        assert result is True

    def test_load_no_key_still_loads(self):
        """HuggingFace can work without a key for some public models."""
        from integrations.providers.huggingface import HuggingFaceProvider

        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            with patch.dict(os.environ, {}, clear=True):
                p = HuggingFaceProvider()
                result = p.load({"model": "test/model"})

        assert result is True

    def test_unload(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()
        p._client = MagicMock()
        p._model = "test"
        assert p.is_loaded()

        p.unload()
        assert not p.is_loaded()

    def test_infer_delegates_to_client(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello from HF"))]
        mock_response.usage.completion_tokens = 5
        mock_client.chat_completion.return_value = mock_response
        p._client = mock_client
        p._model = "test/model"

        response, tokens, elapsed = p.infer("You are helpful.", "Say hi", {"max_tokens": 100})

        assert response == "Hello from HF"
        assert tokens == 5
        mock_client.chat_completion.assert_called_once()

        call_kwargs = mock_client.chat_completion.call_args[1]
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"

    def test_chat_includes_history(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Chat reply"))]
        mock_response.usage.completion_tokens = 3
        mock_client.chat_completion.return_value = mock_response
        p._client = mock_client
        p._model = "test/model"

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        response, tokens, elapsed = p.chat("System", history, "How are you?", {})

        assert response == "Chat reply"
        call_kwargs = mock_client.chat_completion.call_args[1]
        assert len(call_kwargs["messages"]) == 4  # system + 2 history + user

    def test_infer_error_handling(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()

        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = RuntimeError("rate limited")
        p._client = mock_client
        p._model = "test"

        response, tokens, elapsed = p.infer("System", "User", {})

        assert "[inference error:" in response
        assert tokens == 0

    def test_chat_error_handling(self):
        from integrations.providers.huggingface import HuggingFaceProvider
        p = HuggingFaceProvider()

        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = RuntimeError("timeout")
        p._client = mock_client
        p._model = "test"

        response, tokens, elapsed = p.chat("System", [], "User", {})

        assert "[chat error:" in response
        assert tokens == 0

    def test_default_model(self):
        from integrations.providers.huggingface import HuggingFaceProvider

        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            p = HuggingFaceProvider()
            p.load({"api_key": "hf_test"})

        assert p._model == "mistralai/Mistral-7B-Instruct-v0.3"


# ── OpenAIProvider ───────────────────────────────────────────


class TestOpenAIProvider:
    def test_initial_state(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        assert not p.is_loaded()

    def test_load_sets_config(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()

        with patch("urllib.request.urlopen"):
            result = p.load({
                "base_url": "http://localhost:11434/v1",
                "model": "qwen3:8b",
            })

        assert result is True
        assert p.is_loaded()
        assert p._model == "qwen3:8b"
        assert p._base_url == "http://localhost:11434/v1"

    def test_load_fails_without_model(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()

        result = p.load({"base_url": "http://localhost:11434/v1"})

        assert result is False
        assert not p.is_loaded()

    def test_load_fails_without_base_url(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()

        result = p.load({"model": "test"})

        assert result is False

    def test_unload(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost:11434/v1"
        p._model = "test"

        p.unload()

        assert not p.is_loaded()
        assert p._base_url is None
        assert p._model is None

    def test_infer_sends_correct_request(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost:11434/v1"
        p._model = "qwen3:8b"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "API response"}}],
            "usage": {"completion_tokens": 10},
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            response, tokens, elapsed = p.infer("System prompt", "User message", {"max_tokens": 512, "temperature": 0.5})

        assert response == "API response"
        assert tokens == 10

        # Verify request body
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "qwen3:8b"
        assert body["max_tokens"] == 512
        assert body["temperature"] == 0.5
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"

    def test_chat_includes_history(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost:11434/v1"
        p._model = "test"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Chat response"}}],
            "usage": {"completion_tokens": 7},
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            response, tokens, elapsed = p.chat("System", history, "Follow up", {})

        assert response == "Chat response"

        # Verify messages include history
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert len(body["messages"]) == 4  # system + 2 history + user

    def test_infer_with_api_key(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost/v1"
        p._model = "gpt-4"
        p._api_key = "sk-test-key"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"completion_tokens": 1},
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            p.infer("System", "User", {})

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer sk-test-key"

    def test_http_error_handling(self):
        import urllib.error
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost/v1"
        p._model = "test"

        error = urllib.error.HTTPError(
            url="http://localhost/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=b"rate limited")),
        )

        with patch("urllib.request.urlopen", side_effect=error):
            response, tokens, elapsed = p.infer("System", "User", {})

        assert "[API error 429:" in response
        assert tokens == 0

    def test_connection_error_handling(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        p._base_url = "http://localhost:99999/v1"
        p._model = "test"

        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            response, tokens, elapsed = p.infer("System", "User", {})

        assert "[request error:" in response
        assert tokens == 0


# ── ModelManager with providers ──────────────────────────────


class TestModelManagerProviderDispatch:
    def test_backwards_compat_defaults_to_gguf(self, tmp_path):
        """Config without 'backend' field defaults to gguf."""
        import yaml

        config = {
            "models": {
                "A": {
                    "name": "Test",
                    "path": str(tmp_path / "model.gguf"),
                    "n_ctx": 2048,
                    "max_tokens": 512,
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        # The model config should exist and not have backend specified
        cfg = mm._get_model_config("A")
        assert cfg["name"] == "Test"
        assert cfg.get("backend") is None  # not specified, defaults to gguf

    def test_openai_backend_load(self, tmp_path):
        """Config with backend=openai uses OpenAIProvider."""
        import yaml

        config = {
            "models": {
                "A": {
                    "name": "Ollama-Qwen",
                    "backend": "openai",
                    "base_url": "http://localhost:11434/v1",
                    "model": "qwen3:8b",
                    "max_tokens": 1024,
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        with patch("urllib.request.urlopen"):
            result = mm.load("A")

        assert result is True
        assert mm.is_loaded("A")
        assert mm._provider is not None
        assert type(mm._provider).__name__ == "OpenAIProvider"

    def test_strip_think_applied_to_provider_output(self, tmp_path):
        """_strip_think is applied regardless of provider backend."""
        import yaml

        config = {
            "models": {
                "A": {
                    "name": "Test",
                    "backend": "openai",
                    "base_url": "http://localhost/v1",
                    "model": "test",
                    "max_tokens": 100,
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        # Mock the provider
        mock_provider = MagicMock()
        mock_provider.is_loaded.return_value = True
        mock_provider.infer.return_value = (
            "<think>reasoning here</think> Actual response.",
            10,
            0.5,
        )
        mm._provider = mock_provider
        mm._model_sigil = "A"

        response, tokens, elapsed = mm.infer("A", "System", "User")

        assert response == "Actual response."
        assert "<think>" not in response

    def test_missing_config_returns_empty_models(self, tmp_path):
        """ModelManager with nonexistent config file has no models."""
        from integrations.models import ModelManager
        mm = ModelManager(str(tmp_path / "nonexistent.yaml"))

        assert mm.available_models == {}
        assert mm.status()["available"] == []

    def test_load_unknown_sigil(self, tmp_path):
        """Loading a sigil not in config returns False."""
        import yaml

        config = {"models": {"A": {"name": "Test", "backend": "openai", "base_url": "http://x/v1", "model": "m"}}}
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        assert mm.load("Z") is False

    def test_unload_clears_provider(self, tmp_path):
        """Unloading resets provider and sigil."""
        import yaml

        config = {
            "models": {
                "A": {"name": "Test", "backend": "openai", "base_url": "http://x/v1", "model": "m"}
            }
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        with patch("urllib.request.urlopen"):
            mm.load("A")

        assert mm.is_loaded("A")
        mm.unload()
        assert not mm.is_loaded("A")
        assert mm._provider is None

    def test_load_different_sigil_unloads_previous(self, tmp_path):
        """Loading a different sigil unloads the current one first."""
        import yaml

        config = {
            "models": {
                "A": {"name": "A", "backend": "openai", "base_url": "http://x/v1", "model": "a"},
                "B": {"name": "B", "backend": "openai", "base_url": "http://x/v1", "model": "b"},
            }
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        with patch("urllib.request.urlopen"):
            mm.load("A")
            assert mm.is_loaded("A")

            mm.load("B")
            assert mm.is_loaded("B")
            assert not mm.is_loaded("A")
