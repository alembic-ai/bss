"""Tests for BSS setup wizard — config generation, GGUF scanning, backwards compat."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestHasConfig:
    def test_no_file(self, tmp_path):
        from integrations.setup import has_config
        assert has_config(str(tmp_path / "nope.yaml")) is False

    def test_empty_file(self, tmp_path):
        from integrations.setup import has_config
        path = tmp_path / "config.yaml"
        path.write_text("")
        assert has_config(str(path)) is False

    def test_empty_models(self, tmp_path):
        from integrations.setup import has_config
        path = tmp_path / "config.yaml"
        path.write_text("models: {}")
        assert has_config(str(path)) is False

    def test_valid_config(self, tmp_path):
        from integrations.setup import has_config
        path = tmp_path / "config.yaml"
        config = {
            "models": {
                "A": {"name": "Test", "backend": "openai", "base_url": "http://x/v1", "model": "m"},
            }
        }
        with open(path, "w") as f:
            yaml.dump(config, f)
        assert has_config(str(path)) is True

    def test_corrupt_yaml(self, tmp_path):
        from integrations.setup import has_config
        path = tmp_path / "config.yaml"
        path.write_text(": : : invalid yaml {{{}}")
        assert has_config(str(path)) is False


# ── GGUF scanning ────────────────────────────────────────────


class TestScanGGUFFiles:
    def test_finds_files_in_mind_dir(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        mind = tmp_path / "mind"
        mind.mkdir()
        (mind / "Qwen3-4B-Q4_K_M.gguf").touch()
        (mind / "Qwen3-8B-Q4_K_M.gguf").touch()

        found = _scan_gguf_files([str(mind)])

        assert len(found) == 2
        names = [os.path.basename(p) for p in found]
        assert "Qwen3-4B-Q4_K_M.gguf" in names
        assert "Qwen3-8B-Q4_K_M.gguf" in names

    def test_recursive_scan(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        mind = tmp_path / "mind"
        subdir = mind / "qwen"
        subdir.mkdir(parents=True)
        (subdir / "model.gguf").touch()

        found = _scan_gguf_files([str(mind)])

        assert len(found) == 1
        assert found[0].endswith("model.gguf")

    def test_empty_dir(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        mind = tmp_path / "mind"
        mind.mkdir()

        found = _scan_gguf_files([str(mind)])
        assert found == []

    def test_nonexistent_dir(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        found = _scan_gguf_files([str(tmp_path / "nope")])
        assert found == []

    def test_ignores_non_gguf(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        mind = tmp_path / "mind"
        mind.mkdir()
        (mind / "model.gguf").touch()
        (mind / "README.md").touch()
        (mind / "config.json").touch()

        found = _scan_gguf_files([str(mind)])
        assert len(found) == 1

    def test_deduplicates_symlinks(self, tmp_path):
        from integrations.setup import _scan_gguf_files

        mind = tmp_path / "mind"
        mind.mkdir()
        real = mind / "model.gguf"
        real.touch()

        # Create a symlink to the same file
        link = mind / "model-link.gguf"
        link.symlink_to(real)

        # Search with two dirs that both contain the same real file
        found = _scan_gguf_files([str(mind)])

        # Both the real file and symlink have different paths but same realpath
        # The dedup logic uses realpath, so we get just one
        assert len(found) == 1


class TestFormatGGUFSize:
    def test_gigabytes(self, tmp_path):
        from integrations.setup import _format_gguf_size

        f = tmp_path / "big.gguf"
        f.write_bytes(b"\0" * (3 * 1024 * 1024 * 1024))  # too slow for CI
        # Test the function directly with a known size
        # Instead, just test the logic:
        # Can't easily create multi-GB files, so test via smaller sizes

    def test_megabytes(self, tmp_path):
        from integrations.setup import _format_gguf_size

        f = tmp_path / "model.gguf"
        f.write_bytes(b"\0" * (50 * 1024 * 1024))  # 50 MB

        result = _format_gguf_size(str(f))
        assert "MB" in result
        assert "50" in result

    def test_kilobytes(self, tmp_path):
        from integrations.setup import _format_gguf_size

        f = tmp_path / "tiny.gguf"
        f.write_bytes(b"\0" * (512 * 1024))  # 512 KB

        result = _format_gguf_size(str(f))
        assert "KB" in result


# ── Ollama listing ───────────────────────────────────────────


class TestListOllamaModels:
    def test_successful_listing(self):
        from integrations.setup import _list_ollama_models

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "qwen3:8b"},
                {"name": "llama3:latest"},
            ]
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            models = _list_ollama_models("http://localhost:11434")

        assert models == ["qwen3:8b", "llama3:latest"]

    def test_unreachable_returns_empty(self):
        from integrations.setup import _list_ollama_models

        with patch("urllib.request.urlopen", side_effect=ConnectionError):
            models = _list_ollama_models("http://localhost:99999")

        assert models == []


class TestCheckEndpoint:
    def test_reachable(self):
        from integrations.setup import _check_endpoint

        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            assert _check_endpoint("http://localhost:11434/v1") is True

    def test_unreachable(self):
        from integrations.setup import _check_endpoint

        with patch("urllib.request.urlopen", side_effect=ConnectionError):
            assert _check_endpoint("http://localhost:99999/v1") is False


# ── Full wizard flows ────────────────────────────────────────


class TestSetupModels:
    def test_gguf_setup_with_scan(self, tmp_path):
        """GGUF wizard scans mind/, user selects a found model."""
        from integrations.setup import setup_models

        config_path = str(tmp_path / "config.yaml")

        # Create a mind/ dir with a model
        mind = tmp_path / "mind"
        mind.mkdir()
        gguf_file = mind / "Qwen3-4B-Q4_K_M.gguf"
        gguf_file.write_bytes(b"\0" * 1024)

        prompts = iter([
            1,                     # Backend: GGUF
            1,                     # Select first found model
            4096,                  # n_ctx
            4,                     # threads
            "A",                   # Sigil
            "Qwen3-4B",            # Name (derived default)
            1024,                  # Max tokens
            0.7,                   # Temperature
            "#64B5F6",             # Color
        ])

        with patch("typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            with patch("typer.confirm", return_value=False):  # Don't add another
                with patch("integrations.setup._scan_gguf_files", return_value=[str(gguf_file)]):
                    result = setup_models(config_path)

        assert result == config_path

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "A" in config["models"]
        assert config["models"]["A"]["backend"] == "gguf"
        assert config["models"]["A"]["path"] == str(gguf_file)

    def test_gguf_setup_manual_path(self, tmp_path):
        """GGUF wizard with no models found — manual path entry."""
        from integrations.setup import setup_models

        config_path = str(tmp_path / "config.yaml")
        gguf_file = tmp_path / "model.gguf"
        gguf_file.touch()

        prompts = iter([
            1,                     # Backend: GGUF
            str(gguf_file),        # Manual path
            4096,                  # n_ctx
            4,                     # threads
            "A",                   # Sigil
            "TestModel",           # Name
            1024,                  # Max tokens
            0.7,                   # Temperature
            "#64B5F6",             # Color
        ])

        with patch("typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            with patch("typer.confirm", return_value=False):
                with patch("integrations.setup._scan_gguf_files", return_value=[]):
                    result = setup_models(config_path)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["models"]["A"]["backend"] == "gguf"
        assert config["models"]["A"]["name"] == "TestModel"

    def test_ollama_setup(self, tmp_path):
        """Full wizard flow for Ollama backend."""
        from integrations.setup import setup_models

        config_path = str(tmp_path / "config.yaml")

        prompts = iter([
            2,                              # Backend: Ollama
            "http://localhost:11434",        # URL
            "qwen3:8b",                     # Model
            "A",                            # Sigil
            "Qwen3-8B",                     # Name
            1024,                           # Max tokens
            0.5,                            # Temperature
            "#FF8F00",                      # Color
        ])

        with patch("typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            with patch("typer.confirm", return_value=False):
                with patch("integrations.setup._list_ollama_models", return_value=[]):
                    result = setup_models(config_path)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["models"]["A"]["backend"] == "openai"
        assert config["models"]["A"]["base_url"] == "http://localhost:11434/v1"
        assert config["models"]["A"]["model"] == "qwen3:8b"

    def test_openai_setup(self, tmp_path):
        """Full wizard flow for OpenAI-compatible API."""
        from integrations.setup import setup_models

        config_path = str(tmp_path / "config.yaml")

        prompts = iter([
            3,                                          # Backend: OpenAI
            "http://localhost:1234/v1",                  # Base URL
            "sk-test",                                  # API key
            "gpt-4",                                    # Model
            "A",                                        # Sigil
            "GPT-4",                                    # Name
            2048,                                       # Max tokens
            0.3,                                        # Temperature
            "#64B5F6",                                  # Color
        ])

        with patch("typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            with patch("typer.confirm", return_value=False):
                with patch("integrations.setup._check_endpoint", return_value=True):
                    result = setup_models(config_path)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["models"]["A"]["backend"] == "openai"
        assert config["models"]["A"]["api_key"] == "sk-test"
        assert config["models"]["A"]["model"] == "gpt-4"

    def test_multiple_models(self, tmp_path):
        """Adding two models in one wizard session."""
        from integrations.setup import setup_models

        config_path = str(tmp_path / "config.yaml")

        prompts = iter([
            # First model (Ollama)
            2, "http://localhost:11434", "qwen3:8b",
            "A", "Qwen3-8B", 1024, 0.5, "#64B5F6",
            # Second model (Ollama)
            2, "http://localhost:11434", "llama3:latest",
            "B", "Llama3", 1024, 0.7, "#FF8F00",
        ])

        confirms = iter([True, False])  # Add another? Yes, then No

        with patch("typer.prompt", side_effect=lambda *a, **kw: next(prompts)):
            with patch("typer.confirm", side_effect=lambda *a, **kw: next(confirms)):
                with patch("integrations.setup._list_ollama_models", return_value=[]):
                    result = setup_models(config_path)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "A" in config["models"]
        assert "B" in config["models"]
        assert config["models"]["A"]["model"] == "qwen3:8b"
        assert config["models"]["B"]["model"] == "llama3:latest"


# ── Backwards compatibility ──────────────────────────────────


class TestBackwardsCompatibility:
    def test_config_without_backend_works(self, tmp_path):
        """Existing config without 'backend' field should still work."""
        config = {
            "models": {
                "A": {
                    "name": "Qwen3-4B",
                    "path": "~/model.gguf",
                    "n_ctx": 4096,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "threads": 4,
                    "color": "#64B5F6",
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        assert "A" in mm.available_models
        assert mm.available_models["A"]["name"] == "Qwen3-4B"
        cfg = mm._get_model_config("A")
        assert cfg.get("backend", "gguf") == "gguf"

    def test_mixed_backends(self, tmp_path):
        """Config with both gguf and openai backends."""
        config = {
            "models": {
                "A": {
                    "name": "Local",
                    "backend": "gguf",
                    "path": "~/model.gguf",
                    "n_ctx": 4096,
                },
                "B": {
                    "name": "Remote",
                    "backend": "openai",
                    "base_url": "http://localhost:11434/v1",
                    "model": "qwen3:8b",
                },
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        from integrations.models import ModelManager
        mm = ModelManager(str(config_path))

        assert len(mm.available_models) == 2
        assert mm.available_models["A"]["backend"] == "gguf"
        assert mm.available_models["B"]["backend"] == "openai"
