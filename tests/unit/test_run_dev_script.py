from pathlib import Path


def test_run_dev_script_prepares_dirs_without_alembic_before_uvicorn():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_dev.sh"
    script = script_path.read_text(encoding="utf-8")

    prepare_command = "prepare_runtime_dirs"
    server_command = "uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"

    assert "alembic" not in script.lower()
    assert "export ENABLE_REGISTRATION=true" in script
    assert prepare_command in script
    assert server_command in script
    assert script.index("export ENABLE_REGISTRATION=true") < script.index(prepare_command)
    assert script.index(prepare_command) < script.index(server_command)
