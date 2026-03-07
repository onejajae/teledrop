from pathlib import Path


def test_run_dev_script_runs_alembic_before_uvicorn():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_dev.sh"
    script = script_path.read_text(encoding="utf-8")

    migration_command = "uv run alembic -c alembic.ini upgrade head"
    server_command = "uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"

    assert migration_command in script
    assert server_command in script
    assert script.index(migration_command) < script.index(server_command)
