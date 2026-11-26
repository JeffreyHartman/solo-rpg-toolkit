"""Tests that the harness keeps `solo-roll` free of runtime dependencies."""
import subprocess
import sys
import pytest

from solo_roll.campaign import _resolve_repo_root


def test_solo_roll_declares_no_runtime_dependencies():
    tomllib = pytest.importorskip("tomllib")
    pyproject = tomllib.loads((_resolve_repo_root() / "pyproject.toml").read_text())

    assert pyproject["project"]["dependencies"] == []
    assert "fastapi" in " ".join(pyproject["project"]["optional-dependencies"]["harness"])


def test_engine_and_plugins_import_without_the_server_stack():
    probe = (
        "import sys, solo_roll.harness.engine, solo_roll.harness.plugins;"
        "print(sorted(m for m in ('fastapi', 'starlette', 'uvicorn') if m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)

    assert out.stdout.strip() == "[]"
