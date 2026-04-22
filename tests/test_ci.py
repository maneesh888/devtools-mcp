"""Tests for list_projects and run_ci tools."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


SAMPLE_CONFIG = {
    "host_workspace": "/workspace",
    "projects": {
        "just-spent": {"ci": ["./scripts/local-ci.sh --ios", "./scripts/local-ci.sh --quick"]},
        "ai-keyboard": {"ci": ["./scripts/local-ci.sh --ios"]},
        "llm-gateway": {"ci": ["npm test"]},
    },
}


@pytest.fixture(autouse=True)
def clear_config_cache():
    from devtools_mcp.server import _load_projects_config
    _load_projects_config.cache_clear()
    yield
    _load_projects_config.cache_clear()


@pytest.fixture
def mock_config(tmp_path):
    cfg_file = tmp_path / "mcp_helper.json"
    cfg_file.write_text(json.dumps(SAMPLE_CONFIG))
    return cfg_file


def _patch_config(cfg_file):
    return patch("devtools_mcp.server.os.environ.get", return_value=str(cfg_file))


class TestListProjects:
    def test_returns_all_projects(self, mock_config):
        from devtools_mcp.server import list_projects
        with _patch_config(mock_config):
            result = json.loads(list_projects())
        assert set(result.keys()) == {"just-spent", "ai-keyboard", "llm-gateway"}

    def test_includes_ci_commands(self, mock_config):
        from devtools_mcp.server import list_projects
        with _patch_config(mock_config):
            result = json.loads(list_projects())
        assert result["llm-gateway"]["ci"] == ["npm test"]
        assert len(result["just-spent"]["ci"]) == 2

    def test_empty_when_no_config(self, tmp_path):
        from devtools_mcp.server import list_projects
        missing = tmp_path / "missing.json"
        with patch("devtools_mcp.server.os.environ.get", return_value=str(missing)):
            result = json.loads(list_projects())
        assert result == {}


class TestRunCi:
    def test_unknown_project(self, mock_config):
        from devtools_mcp.server import run_ci
        with _patch_config(mock_config):
            result = json.loads(run_ci("nonexistent", "npm test"))
        assert "error" in result
        assert "nonexistent" in result["error"]
        assert "available" in result

    def test_command_not_whitelisted(self, mock_config):
        from devtools_mcp.server import run_ci
        with _patch_config(mock_config):
            result = json.loads(run_ci("llm-gateway", "rm -rf /"))
        assert "error" in result
        assert "whitelisted" in result["error"]
        assert "allowed" in result

    def test_successful_run(self, mock_config):
        from devtools_mcp.server import run_ci
        mock_proc = MagicMock()
        mock_proc.stdout = "Tests passed\n"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            result = json.loads(run_ci("llm-gateway", "npm test"))

        assert result["exit_code"] == 0
        assert result["stdout"] == "Tests passed\n"
        assert result["stderr"] == ""
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["cwd"] == "/workspace/llm-gateway"
        assert call_kwargs.kwargs["timeout"] == 300

    def test_failed_command(self, mock_config):
        from devtools_mcp.server import run_ci
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: test failed"
        mock_proc.returncode = 1

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc):
            result = json.loads(run_ci("llm-gateway", "npm test"))

        assert result["exit_code"] == 1
        assert result["stderr"] == "Error: test failed"

    def test_timeout(self, mock_config):
        import subprocess as sp
        from devtools_mcp.server import run_ci

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", side_effect=sp.TimeoutExpired("npm test", 300)):
            result = json.loads(run_ci("llm-gateway", "npm test"))

        assert result["exit_code"] == -1
        assert "timed out" in result["error"]

    def test_runs_in_correct_directory(self, mock_config):
        from devtools_mcp.server import run_ci
        mock_proc = MagicMock(stdout="ok", stderr="", returncode=0)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            run_ci("just-spent", "./scripts/local-ci.sh --quick")

        assert mock_run.call_args.kwargs["cwd"] == "/workspace/just-spent"

    def test_uses_shlex_not_shell(self, mock_config):
        from devtools_mcp.server import run_ci
        mock_proc = MagicMock(stdout="", stderr="", returncode=0)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            run_ci("llm-gateway", "npm test")

        # Should use list args via shlex.split, not shell=True
        assert mock_run.call_args.args[0] == ["npm", "test"]
        assert "shell" not in mock_run.call_args.kwargs or mock_run.call_args.kwargs.get("shell") is not True
