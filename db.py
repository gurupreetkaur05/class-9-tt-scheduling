"""SQLite persistence for users and projects."""

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

DB_PATH = Path(__file__).parent / "timetable.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed admin user if needed."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            data_json TEXT,
            constraints_json TEXT DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT
        );
    """)
    # Seed admin user if not exists
    existing = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not existing:
        admin_password = st.secrets.get("ADMIN_PASSWORD", "admin@123")
        salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256((salt + admin_password).encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            ("admin", pw_hash, salt, "admin"),
        )
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(username: str, password: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        return False
    return row["password_hash"] == _hash_password(password, row["salt"])


def get_user(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT id, username, role FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


def create_user(username: str, password: str, role: str = "user") -> bool:
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_user(username: str) -> bool:
    if username == "admin":
        return False
    conn = get_connection()
    cur = conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def list_users() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"], "role": r["role"]} for r in rows]


# --- Project CRUD ---

def create_project(name: str, owner: str) -> int:
    now = datetime.now().isoformat()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO projects (name, owner_username, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (name, owner, now, now),
    )
    conn.commit()
    project_id = cur.lastrowid
    conn.close()
    return project_id


def get_project(project_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_projects(owner: str | None = None) -> list[dict]:
    conn = get_connection()
    if owner:
        rows = conn.execute(
            "SELECT id, name, owner_username, created_at, updated_at FROM projects WHERE owner_username = ? ORDER BY updated_at DESC",
            (owner,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, owner_username, created_at, updated_at FROM projects ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_project(project_id: int, data_json: str | None = None, constraints_json: str | None = None):
    now = datetime.now().isoformat()
    conn = get_connection()
    if data_json is not None:
        conn.execute("UPDATE projects SET data_json = ?, updated_at = ? WHERE id = ?", (data_json, now, project_id))
    if constraints_json is not None:
        conn.execute("UPDATE projects SET constraints_json = ?, updated_at = ? WHERE id = ?", (constraints_json, now, project_id))
    conn.commit()
    conn.close()


def delete_project(project_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
