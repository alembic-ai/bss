"""Tests for BSS auto-discovery — GGUF scanning, endpoint probing, env var detection."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from integrations.discovery import (
    DiscoveryResult,
    DiscoveryReport,
    scan_gguf_files,
    list_ollama_models,
    check_endpoint,
    format_gguf_size,
    discover_gguf,
    discover_ollama,
    discover_openai_endpoints,
    discover_anthropic,
    discover_gemini,
    discover_huggingface,
    discover_all,
)


# ── Data structures ─────────────────────────────────────────


class TestDiscoveryResult:
    def test_fields(self):
        r = DiscoveryResult(
            backend="gguf",
            source="scan",
            label="model.gguf (4.0 GB)",
            available=True,
            details={"path": "/tmp/model.gguf"},
        )
        assert r.backend == "gguf"
        assert r.source == "scan"
        assert r.available is True
        assert r.details["path"] == "/tmp/model.gguf"

    def test_defaults(self):
        r = DiscoveryResult(backend="openai", source="endpoint", label="test", available=False)
        assert r.details == {}


class TestDiscoveryReport:
    def test_empty_report(self):
        report = DiscoveryReport()
        assert report.results == []
        assert report.elapsed == 0.0

    def test_report_with_results(self):
        r = DiscoveryResult(backend="gguf", source="scan", label="test", available=True)
        report = DiscoveryReport(results=[r], elapsed=0.5)
        assert len(report.results) == 1
        assert report.elapsed == 0.5


# ── Scanning functions ──────────────────────────────────────


class TestScanGGUFFiles:
    def test_finds_files(self, tmp_path):
        mind = tmp_path / "mind"
        mind.mkdir()
        (mind / "model.gguf").touch()

        found = scan_gguf_files([str(mind)])
        assert len(found) == 1
        assert found[0].endswith("model.gguf")

    def test_recursive(self, tmp_path):
        subdir = tmp_path / "mind" / "sub"
        subdir.mkdir(parents=True)
        (subdir / "nested.gguf").touch()

        found = scan_gguf_files([str(tmp_path / "mind")])
        assert len(found) == 1

    def test_empty_dir(self, tmp_path):
        mind = tmp_path / "mind"
        mind.mkdir()
        assert scan_gguf_files([str(mind)]) == []

    def test_nonexistent_dir(self, tmp_path):
        assert scan_gguf_files([str(tmp_path / "nope")]) == []

    def test_deduplicates(self, tmp_path):
        mind = tmp_path / "mind"
        mind.mkdir()
        real = mind / "model.gguf"
        real.touch()
        link = mind / "link.gguf"
        link.symlink_to(real)

        found = scan_gguf_files([str(mind)])
        assert len(found) == 1


class TestListOllamaModels:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [{"name": "qwen3:8b"}, {"name": "llama3:latest"}]
        }).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = list_ollama_models("http://localhost:11434")
        assert models == ["qwen3:8b", "llama3:latest"]

    def test_failure(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError):
            assert list_ollama_models() == []


class TestCheckEndpoint:
    def test_reachable(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert check_endpoint("http://localhost:1234/v1") is True

    def test_unreachable(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError):
            assert check_endpoint("http://localhost:99999/v1") is False

    def test_with_api_key(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            check_endpoint("http://localhost:1234/v1", api_key="sk-test")
            req = mock_urlopen.call_args[0][0]
            assert req.get_header("Authorization") == "Bearer sk-test"


class TestFormatGGUFSize:
    def test_megabytes(self, tmp_path):
        f = tmp_path / "model.gguf"
        f.write_bytes(b"\0" * (50 * 1024 * 1024))
        result = format_gguf_size(str(f))
        assert "MB" in result

    def test_kilobytes(self, tmp_path):
        f = tmp_path / "tiny.gguf"
        f.write_bytes(b"\0" * (512 * 1024))
        result = format_gguf_size(str(f))
        assert "KB" in result


# ── Per-backend discovery ───────────────────────────────────


class TestDiscoverGGUF:
    def test_finds_models(self, tmp_path):
        mind = tmp_path / "mind"
        mind.mkdir()
        (mind / "model.gguf").write_bytes(b"\0" * 1024)

        results = discover_gguf([str(mind)])
        assert len(results) == 1
        assert results[0].backend == "gguf"
        assert results[0].source == "scan"
        assert results[0].available is True
        assert "model.gguf" in results[0].label

    def test_empty(self, tmp_path):
        assert discover_gguf([str(tmp_path / "nope")]) == []


class TestDiscoverOllama:
    def test_finds_models(self):
        with patch("integrations.discovery.list_ollama_models", return_value=["qwen3:8b", "llama3:latest"]):
            results = discover_ollama()

        assert len(results) == 2
        assert results[0].backend == "openai"
        assert results[0].source == "endpoint"
        assert "qwen3:8b" in results[0].label
        assert results[0].details["server"] == "ollama"

    def test_no_ollama(self):
        with patch("integrations.discovery.list_ollama_models", return_value=[]):
            results = discover_ollama()
        assert results == []


class TestDiscoverOpenAIEndpoints:
    def test_finds_endpoints(self):
        def mock_check(url, api_key=None):
            return "localhost:1234" in url

        with patch("integrations.discovery.check_endpoint", side_effect=mock_check):
            results = discover_openai_endpoints()

        assert len(results) == 1
        assert "LM Studio" in results[0].label

    def test_no_endpoints(self):
        with patch("integrations.discovery.check_endpoint", return_value=False):
            results = discover_openai_endpoints()
        assert results == []


class TestDiscoverAnthropic:
    def test_key_present(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-abcdefghijklmnop"}):
            results = discover_anthropic()
        assert len(results) == 1
        assert results[0].backend == "anthropic"
        assert results[0].source == "env_var"

    def test_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            results = discover_anthropic()
        assert results == []


class TestDiscoverGemini:
    def test_google_key(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "AIzaSyTest1234"}):
            results = discover_gemini()
        assert len(results) == 1
        assert results[0].backend == "gemini"

    def test_gemini_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTest5678"}, clear=True):
            results = discover_gemini()
        assert len(results) == 1

    def test_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            results = discover_gemini()
        assert results == []


class TestDiscoverHuggingFace:
    def test_hf_token(self):
        with patch.dict(os.environ, {"HF_TOKEN": "hf_abcdefghij"}):
            results = discover_huggingface()
        assert len(results) == 1
        assert results[0].backend == "huggingface"

    def test_hub_token(self):
        with patch.dict(os.environ, {"HUGGING_FACE_HUB_TOKEN": "hf_xyz"}, clear=True):
            results = discover_huggingface()
        assert len(results) == 1

    def test_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            results = discover_huggingface()
        assert results == []


# ── Aggregate discovery ─────────────────────────────────────


class TestDiscoverAll:
    def test_aggregates_results(self, tmp_path):
        mind = tmp_path / "mind"
        mind.mkdir()
        (mind / "model.gguf").write_bytes(b"\0" * 1024)

        with patch("integrations.discovery.list_ollama_models", return_value=["qwen3:8b"]):
            with patch("integrations.discovery.check_endpoint", return_value=False):
                with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test1234567890"}, clear=True):
                    report = discover_all(gguf_dirs=[str(mind)])

        assert isinstance(report, DiscoveryReport)
        assert report.elapsed >= 0

        backends = [r.backend for r in report.results]
        assert "gguf" in backends
        assert "openai" in backends  # ollama
        assert "anthropic" in backends

    def test_empty_environment(self, tmp_path):
        with patch("integrations.discovery.list_ollama_models", return_value=[]):
            with patch("integrations.discovery.check_endpoint", return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    report = discover_all(gguf_dirs=[str(tmp_path / "nope")])

        assert report.results == []
        assert report.elapsed >= 0


# ── Backward compat: setup.py still exposes private names ───


class TestSetupBackwardCompat:
    def test_scan_gguf_files_alias(self):
        from integrations.setup import _scan_gguf_files
        assert _scan_gguf_files is scan_gguf_files

    def test_list_ollama_models_alias(self):
        from integrations.setup import _list_ollama_models
        assert _list_ollama_models is list_ollama_models

    def test_check_endpoint_alias(self):
        from integrations.setup import _check_endpoint
        assert _check_endpoint is check_endpoint

    def test_format_gguf_size_alias(self):
        from integrations.setup import _format_gguf_size
        assert _format_gguf_size is format_gguf_size
