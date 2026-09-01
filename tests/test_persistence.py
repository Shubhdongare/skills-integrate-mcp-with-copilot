import importlib
import os
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def load_app(db_path: Path):
    os.environ["ACTIVITY_DB_PATH"] = str(db_path)
    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")
    importlib.reload(app_module)
    return app_module


def test_signup_persists_across_app_restart(tmp_path):
    db_path = tmp_path / "activities.db"
    app_module = load_app(db_path)
    client = TestClient(app_module.app)

    response = client.post("/activities/Chess Club/signup?email=student@mergington.edu")

    assert response.status_code == 200
    assert "student@mergington.edu" in response.json()["message"]

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT email FROM activity_participants WHERE activity_name = 'Chess Club'"
        ).fetchall()

    emails = {row[0] for row in rows}
    assert "student@mergington.edu" in emails

    reloaded_module = load_app(db_path)
    refreshed = reloaded_module.get_activities()
    assert "student@mergington.edu" in refreshed["Chess Club"]["participants"]


def test_get_activities_returns_complete_activity_data(tmp_path):
    db_path = tmp_path / "activities.db"
    app_module = load_app(db_path)
    client = TestClient(app_module.app)

    response = client.get("/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert "description" in data["Chess Club"]
    assert "schedule" in data["Chess Club"]
    assert "max_participants" in data["Chess Club"]
    assert "participants" in data["Chess Club"]
