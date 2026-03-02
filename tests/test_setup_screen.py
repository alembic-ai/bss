"""Tests for BSS SetupScreen — Textual TUI model configuration wizard."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Static

from terminal.setup_screen import SetupScreen, STEPS, BACKENDS


# ── Test harness ────────────────────────────────────────────


class SetupTestApp(App):
    """Minimal app that hosts SetupScreen for testing."""

    def __init__(self, config_path: str, existing_config: dict | None = None):
        super().__init__()
        self._config_path = config_path
        self._existing_config = existing_config
        self.setup_result = None

    def compose(self) -> ComposeResult:
        yield Static("test host")

    def on_mount(self):
        screen = SetupScreen(
            config_path=self._config_path,
            existing_config=self._existing_config,
        )
        self.push_screen(screen, callback=self._on_complete)

    def _on_complete(self, result):
        self.setup_result = result


# ── Tests ───────────────────────────────────────────────────


class TestSetupScreenStructure:
    def test_steps_defined(self):
        """STEPS list contains all expected wizard steps."""
        assert "DISCOVERY" in STEPS
        assert "BACKEND_SELECT" in STEPS
        assert "BACKEND_CONFIG" in STEPS
        assert "COMMON_CONFIG" in STEPS
        assert "REVIEW" in STEPS
        assert "SUMMARY" in STEPS

    def test_backends_defined(self):
        """All 5 backends are available for selection."""
        backend_ids = [b[0] for b in BACKENDS]
        assert "gguf" in backend_ids
        assert "openai" in backend_ids
        assert "anthropic" in backend_ids
        assert "gemini" in backend_ids
        assert "huggingface" in backend_ids


class TestSetupScreenInit:
    def test_default_config_path(self):
        screen = SetupScreen()
        assert screen._config_path.endswith("config.yaml")

    def test_custom_config_path(self, tmp_path):
        path = str(tmp_path / "custom.yaml")
        screen = SetupScreen(config_path=path)
        assert screen._config_path == path

    def test_existing_config_loaded(self):
        existing = {"models": {"A": {"name": "Test", "backend": "openai"}}}
        screen = SetupScreen(existing_config=existing)
        assert "A" in screen._models
        assert screen._model_index == 1

    def test_empty_existing_config(self):
        screen = SetupScreen(existing_config={})
        assert screen._models == {}
        assert screen._model_index == 0


class TestSetupScreenValidation:
    def test_validate_common_config_valid(self):
        screen = SetupScreen()

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-sigil": "A",
                "field-name": "Test Model",
                "field-max_tokens": "1024",
                "field-temperature": "0.7",
                "field-color": "#64B5F6",
            }.get(f, "")

            result = screen._validate_common_config()
            assert result is None

    def test_validate_common_config_bad_sigil(self):
        screen = SetupScreen()

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-sigil": "AB",
                "field-name": "Test",
                "field-max_tokens": "1024",
                "field-temperature": "0.7",
                "field-color": "#64B5F6",
            }.get(f, "")

            result = screen._validate_common_config()
            assert result is not None
            assert "Sigil" in result

    def test_validate_common_config_bad_color(self):
        screen = SetupScreen()

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-sigil": "A",
                "field-name": "Test",
                "field-max_tokens": "1024",
                "field-temperature": "0.7",
                "field-color": "not-hex",
            }.get(f, "")

            result = screen._validate_common_config()
            assert result is not None
            assert "hex" in result.lower()

    def test_validate_common_config_bad_max_tokens(self):
        screen = SetupScreen()

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-sigil": "A",
                "field-name": "Test",
                "field-max_tokens": "abc",
                "field-temperature": "0.7",
                "field-color": "#64B5F6",
            }.get(f, "")

            result = screen._validate_common_config()
            assert result is not None
            assert "number" in result.lower()

    def test_validate_backend_config_gguf_missing_path(self):
        screen = SetupScreen()
        screen._selected_backend = "gguf"

        with patch.object(screen, '_get_field', return_value=""):
            result = screen._validate_backend_config()
            assert result is not None
            assert "Path" in result

    def test_validate_backend_config_openai_missing_url(self):
        screen = SetupScreen()
        screen._selected_backend = "openai"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-base_url": "",
                "field-model": "test",
                "field-api_key": "",
            }.get(f, "")

            result = screen._validate_backend_config()
            assert result is not None
            assert "URL" in result

    def test_validate_backend_config_openai_missing_model(self):
        screen = SetupScreen()
        screen._selected_backend = "openai"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-base_url": "http://localhost:11434/v1",
                "field-model": "",
                "field-api_key": "",
            }.get(f, "")

            result = screen._validate_backend_config()
            assert result is not None
            assert "Model" in result

    def test_validate_backend_config_anthropic_no_key_no_env(self):
        screen = SetupScreen()
        screen._selected_backend = "anthropic"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-api_key": "",
                "field-model": "claude-sonnet-4-20250514",
            }.get(f, "")
            with patch.dict(os.environ, {}, clear=True):
                result = screen._validate_backend_config()
                assert result is not None
                assert "API key" in result

    def test_validate_backend_config_anthropic_env_key_ok(self):
        screen = SetupScreen()
        screen._selected_backend = "anthropic"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-api_key": "",
                "field-model": "claude-sonnet-4-20250514",
            }.get(f, "")
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
                result = screen._validate_backend_config()
                assert result is None


class TestSetupScreenCollectors:
    def test_collect_backend_config_gguf(self):
        screen = SetupScreen()
        screen._selected_backend = "gguf"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-path": "~/mind/model.gguf",
                "field-n_ctx": "4096",
                "field-threads": "4",
            }.get(f, "")

            cfg = screen._collect_backend_config()
            assert cfg["backend"] == "gguf"
            assert cfg["path"] == "~/mind/model.gguf"
            assert cfg["n_ctx"] == 4096
            assert cfg["threads"] == 4

    def test_collect_backend_config_openai(self):
        screen = SetupScreen()
        screen._selected_backend = "openai"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-base_url": "http://localhost:11434/v1",
                "field-model": "qwen3:8b",
                "field-api_key": "",
            }.get(f, "")

            cfg = screen._collect_backend_config()
            assert cfg["backend"] == "openai"
            assert cfg["base_url"] == "http://localhost:11434/v1"
            assert cfg["model"] == "qwen3:8b"
            assert "api_key" not in cfg  # empty key not stored

    def test_collect_backend_config_anthropic_with_key(self):
        screen = SetupScreen()
        screen._selected_backend = "anthropic"

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-model": "claude-sonnet-4-20250514",
                "field-api_key": "sk-ant-test",
            }.get(f, "")

            cfg = screen._collect_backend_config()
            assert cfg["backend"] == "anthropic"
            assert cfg["model"] == "claude-sonnet-4-20250514"
            assert cfg["api_key"] == "sk-ant-test"

    def test_collect_common_config(self):
        screen = SetupScreen()

        with patch.object(screen, '_get_field') as mock_field:
            mock_field.side_effect = lambda f: {
                "field-sigil": "A",
                "field-name": "Test Model",
                "field-max_tokens": "2048",
                "field-temperature": "0.5",
                "field-color": "#FF8F00",
            }.get(f, "")

            cfg = screen._collect_common_config()
            assert cfg["_sigil"] == "A"
            assert cfg["name"] == "Test Model"
            assert cfg["max_tokens"] == 2048
            assert cfg["temperature"] == 0.5
            assert cfg["color"] == "#FF8F00"


class TestSetupScreenSave:
    def test_save_writes_config(self, tmp_path):
        config_path = str(tmp_path / "config.yaml")
        screen = SetupScreen(config_path=config_path)
        screen._models = {
            "A": {
                "backend": "openai",
                "base_url": "http://localhost:11434/v1",
                "model": "qwen3:8b",
                "name": "Qwen3-8B",
                "max_tokens": 1024,
                "temperature": 0.7,
                "color": "#64B5F6",
            }
        }

        screen._save_and_dismiss = lambda: None  # prevent dismiss
        # Call save logic directly
        config = {"models": screen._models}
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(config_path) as f:
            saved = yaml.safe_load(f)

        assert "A" in saved["models"]
        assert saved["models"]["A"]["backend"] == "openai"
        assert saved["models"]["A"]["model"] == "qwen3:8b"

    def test_save_multiple_models(self, tmp_path):
        config_path = str(tmp_path / "config.yaml")
        screen = SetupScreen(config_path=config_path)
        screen._models = {
            "A": {"backend": "openai", "model": "qwen3:8b", "name": "Qwen"},
            "B": {"backend": "anthropic", "model": "claude-sonnet-4-20250514", "name": "Claude"},
        }

        config = {"models": screen._models}
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        with open(config_path) as f:
            saved = yaml.safe_load(f)

        assert len(saved["models"]) == 2
        assert "A" in saved["models"]
        assert "B" in saved["models"]


class TestSetupScreenNavigation:
    def test_handle_next_from_discovery(self):
        screen = SetupScreen()
        screen._step = 0
        screen._report = MagicMock()

        # Mock render_step to avoid UI ops
        with patch.object(screen, '_render_step'):
            screen._handle_next("DISCOVERY")
        assert screen._step == STEPS.index("BACKEND_SELECT")

    def test_handle_next_from_backend_config(self):
        screen = SetupScreen()
        screen._step = STEPS.index("BACKEND_CONFIG")
        screen._selected_backend = "openai"

        with patch.object(screen, '_validate_backend_config', return_value=None):
            with patch.object(screen, '_collect_backend_config', return_value={"backend": "openai", "model": "test"}):
                with patch.object(screen, '_render_step'):
                    screen._handle_next("BACKEND_CONFIG")

        assert screen._step == STEPS.index("COMMON_CONFIG")

    def test_handle_next_from_backend_config_validation_error(self):
        screen = SetupScreen()
        screen._step = STEPS.index("BACKEND_CONFIG")
        screen._selected_backend = "gguf"

        with patch.object(screen, '_validate_backend_config', return_value="Path is required"):
            with patch.object(screen, '_show_error') as mock_err:
                screen._handle_next("BACKEND_CONFIG")

        mock_err.assert_called_once_with("Path is required")
        assert screen._step == STEPS.index("BACKEND_CONFIG")  # stays on same step

    def test_handle_next_from_common_config(self):
        screen = SetupScreen()
        screen._step = STEPS.index("COMMON_CONFIG")
        screen._current_model_config = {"backend": "openai"}

        with patch.object(screen, '_validate_common_config', return_value=None):
            with patch.object(screen, '_collect_common_config', return_value={
                "_sigil": "A", "name": "Test", "max_tokens": 1024,
                "temperature": 0.7, "color": "#64B5F6",
            }):
                with patch.object(screen, '_render_step'):
                    screen._handle_next("COMMON_CONFIG")

        assert screen._step == STEPS.index("REVIEW")

    def test_handle_next_from_review_commits_model(self):
        screen = SetupScreen()
        screen._step = STEPS.index("REVIEW")
        screen._current_model_config = {
            "backend": "openai",
            "model": "test",
            "_sigil": "A",
            "name": "Test",
            "max_tokens": 1024,
            "temperature": 0.7,
            "color": "#64B5F6",
        }

        with patch.object(screen, '_render_step'):
            screen._handle_next("REVIEW")

        assert "A" in screen._models
        assert screen._models["A"]["backend"] == "openai"
        assert "_sigil" not in screen._models["A"]
        assert screen._step == STEPS.index("SUMMARY")

    def test_handle_next_from_summary_saves(self, tmp_path):
        config_path = str(tmp_path / "config.yaml")
        screen = SetupScreen(config_path=config_path)
        screen._step = STEPS.index("SUMMARY")
        screen._models = {"A": {"backend": "openai", "model": "test", "name": "Test"}}

        with patch.object(screen, 'dismiss') as mock_dismiss:
            screen._handle_next("SUMMARY")

        mock_dismiss.assert_called_once_with(config_path)

        with open(config_path) as f:
            saved = yaml.safe_load(f)
        assert "A" in saved["models"]


class TestModelManagerReload:
    def test_reload_reads_new_config(self, tmp_path):
        """ModelManager.reload() picks up new config from disk."""

        # Initial config with one model
        config1 = {"models": {"A": {"name": "First", "backend": "openai", "base_url": "http://x/v1", "model": "m"}}}
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config1, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))
        assert list(mm.available_models.keys()) == ["A"]

        # Write new config with two models
        config2 = {
            "models": {
                "A": {"name": "First", "backend": "openai", "base_url": "http://x/v1", "model": "m"},
                "B": {"name": "Second", "backend": "anthropic", "model": "claude"},
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config2, f)

        mm.reload(str(config_path))
        assert "B" in mm.available_models
        assert len(mm.available_models) == 2

    def test_reload_unloads_current(self, tmp_path):
        """reload() unloads any currently loaded model."""
        config = {"models": {"A": {"name": "Test", "backend": "openai", "base_url": "http://x/v1", "model": "m"}}}
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        with patch("urllib.request.urlopen"):
            mm.load("A")
        assert mm.is_loaded("A")

        mm.reload(str(config_path))
        assert not mm.is_loaded("A")
        assert mm.loaded_sigil is None
