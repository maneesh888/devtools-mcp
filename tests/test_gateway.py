"""Tests for gateway_build, gateway_start, and gateway_stop tools."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest


SAMPLE_CONFIG = {
    "host_workspace": "/workspace",
    "projects": {},
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


class TestGatewayBuild:
    def test_success(self, mock_config):
        from devtools_mcp.server import gateway_build
        mock_proc = MagicMock(stdout="ok\n", stderr="", returncode=0)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            result = json.loads(gateway_build())

        assert result["success"] is True
        assert result["exit_code"] == 0
        # Two calls: npm install, then npm run build
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0].args[0] == ["npm", "install"]
        assert mock_run.call_args_list[1].args[0] == ["npm", "run", "build"]
        assert mock_run.call_args_list[0].kwargs["cwd"] == "/workspace/llm-gateway"

    def test_install_failure_skips_build(self, mock_config):
        from devtools_mcp.server import gateway_build
        mock_proc = MagicMock(stdout="", stderr="install error", returncode=1)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            result = json.loads(gateway_build())

        assert result["success"] is False
        assert result["stage"] == "npm install"
        # Should only call npm install, not proceed to build
        assert mock_run.call_count == 1

    def test_build_failure(self, mock_config):
        from devtools_mcp.server import gateway_build
        install_ok = MagicMock(stdout="", stderr="", returncode=0)
        build_fail = MagicMock(stdout="", stderr="compile error", returncode=1)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run", side_effect=[install_ok, build_fail]):
            result = json.loads(gateway_build())

        assert result["success"] is False
        assert result["exit_code"] == 1
        assert result["stderr"] == "compile error"

    def test_timeout(self, mock_config):
        from devtools_mcp.server import gateway_build

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("npm", 120)):
            result = json.loads(gateway_build())

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "timed out" in result["error"].lower()

    def test_exception(self, mock_config):
        from devtools_mcp.server import gateway_build

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.run",
                   side_effect=FileNotFoundError("npm not found")):
            result = json.loads(gateway_build())

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "npm not found" in result["error"]

    def test_uses_host_workspace_from_config(self, tmp_path):
        from devtools_mcp.server import gateway_build
        cfg = {"host_workspace": "/custom/workspace", "projects": {}}
        cfg_file = tmp_path / "mcp_helper.json"
        cfg_file.write_text(json.dumps(cfg))
        mock_proc = MagicMock(stdout="", stderr="", returncode=0)

        with patch("devtools_mcp.server.os.environ.get", return_value=str(cfg_file)), \
             patch("devtools_mcp.server.subprocess.run", return_value=mock_proc) as mock_run:
            gateway_build()

        assert mock_run.call_args_list[0].kwargs["cwd"] == "/custom/workspace/llm-gateway"


class TestGatewayStart:
    def test_success(self, mock_config):
        from devtools_mcp.server import gateway_start
        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.Popen", return_value=mock_proc) as mock_popen, \
             patch("builtins.open", mock_open()):
            result = json.loads(gateway_start())

        assert result["pid"] == 12345
        assert result["status"] == "started"
        assert result["port"] == 8081
        assert mock_popen.call_args.args[0] == ["npm", "start"]
        assert mock_popen.call_args.kwargs["cwd"] == "/workspace/llm-gateway"

    def test_custom_port(self, mock_config):
        from devtools_mcp.server import gateway_start
        mock_proc = MagicMock(pid=99)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.Popen", return_value=mock_proc), \
             patch("builtins.open", mock_open()):
            result = json.loads(gateway_start(port=9000))

        assert result["port"] == 9000
        assert result["status"] == "started"

    def test_port_passed_in_env(self, mock_config):
        from devtools_mcp.server import gateway_start
        mock_proc = MagicMock(pid=42)

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.Popen", return_value=mock_proc) as mock_popen, \
             patch("builtins.open", mock_open()):
            gateway_start(port=3000)

        env = mock_popen.call_args.kwargs["env"]
        assert env["PORT"] == "3000"

    def test_popen_exception(self, mock_config):
        from devtools_mcp.server import gateway_start

        with _patch_config(mock_config), \
             patch("devtools_mcp.server.subprocess.Popen",
                   side_effect=FileNotFoundError("npm not found")), \
             patch("builtins.open", mock_open()):
            result = json.loads(gateway_start())

        assert result["status"] == "failed"
        assert "npm not found" in result["error"]


class TestGatewayStop:
    def test_stops_running_process(self, tmp_path):
        from devtools_mcp.server import gateway_stop

        pid_file = tmp_path / "llm-gateway.pid"
        pid_file.write_text("12345\n")

        with patch("devtools_mcp.server._gateway_log_dir", return_value=tmp_path), \
             patch("devtools_mcp.server.os.kill") as mock_kill:
            result = json.loads(gateway_stop())

        assert result["success"] is True
        mock_kill.assert_called_once_with(12345, 15)

    def test_no_pid_file(self, tmp_path):
        from devtools_mcp.server import gateway_stop

        with patch("devtools_mcp.server._gateway_log_dir", return_value=tmp_path):
            result = json.loads(gateway_stop())

        assert result["success"] is False
        assert "not be running" in result["message"]
