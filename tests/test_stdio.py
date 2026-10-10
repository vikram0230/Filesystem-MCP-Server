import json
import subprocess
import sys
from pathlib import Path


def _run(args: list[str], stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "filesystem_mcp", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_no_directory_exits_before_any_json() -> None:
    completed = _run([])

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "Usage: filesystem-mcp" in completed.stderr


def test_missing_directory_exits_before_any_json(tmp_path: Path) -> None:
    completed = _run([str(tmp_path / "missing")])

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "does not exist" in completed.stderr


def test_initialize_returns_one_jsonrpc_response(tmp_path: Path) -> None:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.0.0"},
        },
    }
    completed = _run([str(tmp_path)], json.dumps(request) + "\n")
    lines = completed.stdout.splitlines()

    assert completed.returncode == 0
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "filesystem"
    assert "tools" in response["result"]["capabilities"]
