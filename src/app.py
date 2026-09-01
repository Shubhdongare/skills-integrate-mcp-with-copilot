"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

DB_PATH = Path(os.getenv("ACTIVITY_DB_PATH", Path(__file__).with_name("activities.db")))

DEFAULT_ACTIVITIES = [
    {
        "name": "Chess Club",
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    {
        "name": "Programming Class",
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    {
        "name": "Gym Class",
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    {
        "name": "Soccer Team",
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    {
        "name": "Basketball Team",
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    {
        "name": "Art Club",
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    {
        "name": "Drama Club",
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    {
        "name": "Math Club",
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    {
        "name": "Debate Team",
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
]

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_participants (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY (activity_name) REFERENCES activities(name)
            )
            """
        )

        if conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0:
            for activity in DEFAULT_ACTIVITIES:
                conn.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (activity["name"], activity["description"], activity["schedule"], activity["max_participants"]),
                )
                for email in activity["participants"]:
                    conn.execute(
                        "INSERT INTO activity_participants (activity_name, email) VALUES (?, ?)",
                        (activity["name"], email),
                    )


initialize_database()


def get_activity_details(activity_name: str):
    with get_db_connection() as conn:
        activity = conn.execute(
            "SELECT name, description, schedule, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        participants = [
            row["email"]
            for row in conn.execute(
                "SELECT email FROM activity_participants WHERE activity_name = ? ORDER BY email",
                (activity_name,),
            ).fetchall()
        ]

        return {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": participants,
        }


def get_activities():
    with get_db_connection() as conn:
        activities = {}
        for row in conn.execute(
            "SELECT name, description, schedule, max_participants FROM activities ORDER BY name"
        ).fetchall():
            participants = [
                participant_row["email"]
                for participant_row in conn.execute(
                    "SELECT email FROM activity_participants WHERE activity_name = ? ORDER BY email",
                    (row["name"],),
                ).fetchall()
            ]
            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": participants,
            }
    return activities


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities_endpoint():
    return get_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity."""
    activity = get_activity_details(activity_name)
    participants = activity["participants"]

    if email in participants:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if len(participants) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO activity_participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email),
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity."""
    activity = get_activity_details(activity_name)
    participants = activity["participants"]

    if email not in participants:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM activity_participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )

    return {"message": f"Unregistered {email} from {activity_name}"}
