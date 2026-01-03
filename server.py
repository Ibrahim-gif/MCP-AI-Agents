# Import dependencies

from mcp.server.fastmcp import FastMCP 
import json 
from typing import List, Optional, Any
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime

# Set up FastMCP server
mcp = FastMCP("todo_mcp_server")

DB_FILENAME = "todo_db.json"

# Put DB next to this script (not CWD-dependent)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)

_lock = threading.Lock()

@dataclass
class Task:
    id: int
    title: str
    due_date: Optional[str] = None
    completed: bool = False
    created_at: str = ""
    completed_at: Optional[str] = None


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _default_db() -> dict[str, Any]:
    return {"next_id": 1, "tasks": []}


def _load_db() -> dict[str, Any]:
    if not os.path.exists(DB_PATH):
        return _default_db()

    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # If file is corrupted, start fresh rather than crashing the server
            return _default_db()

    # Basic shape validation / migration safety
    if not isinstance(data, dict):
        return _default_db()
    if "next_id" not in data or "tasks" not in data:
        return _default_db()
    if not isinstance(data["tasks"], list):
        data["tasks"] = []
    if not isinstance(data["next_id"], int) or data["next_id"] < 1:
        data["next_id"] = 1

    return data


def _save_db(data: dict[str, Any]) -> None:
    tmp_path = DB_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DB_PATH)


def _task_from_dict(d: dict[str, Any]) -> Task:
    # Graceful parsing if older tasks are missing fields
    return Task(
        id=int(d.get("id")),
        title=str(d.get("title", "")),
        due_date=d.get("due_date"),
        completed=bool(d.get("completed", False)),
        created_at=str(d.get("created_at", "")) or _now_iso(),
        completed_at=d.get("completed_at"),
    )


def _serialize_task(t: Task) -> dict[str, Any]:
    return asdict(t)


@mcp.tool()
def add_task(title: str, due_date: Optional[str] = None) -> dict[str, Any]:
    """
    Create a new task.

    Args:
      title: Task title (required, non-empty).
      due_date: Optional due date string, e.g. "2026-01-15".

    Returns:
      The created task as a dict.
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("title must be a non-empty string")

    with _lock:
        db = _load_db()
        task_id = db["next_id"]
        db["next_id"] += 1

        task = Task(
            id=task_id,
            title=title,
            due_date=(due_date.strip() if isinstance(due_date, str) and due_date.strip() else None),
            completed=False,
            created_at=_now_iso(),
            completed_at=None,
        )

        db["tasks"].append(_serialize_task(task))
        _save_db(db)

    return _serialize_task(task)


@mcp.tool()
def list_tasks(is_completed: bool = False) -> list[dict[str, Any]]:
    """
    List tasks if they are completed or not.
    Args:
      is_completed: If True, list completed tasks; else list incomplete tasks.

    Returns:
      List of task dicts, sorted by completion (incomplete first), then id asc.
    """
    with _lock:
        db = _load_db()
        tasks = [_task_from_dict(t) for t in db["tasks"] if bool(t.get("completed", False)) == is_completed]

    tasks.sort(key=lambda t: (t.completed, t.id))
    return [_serialize_task(t) for t in tasks]


@mcp.tool()
def complete_task(task_id: int) -> dict[str, Any]:
    """
    Mark a task as completed.

    Args:
      task_id: The integer ID of the task.

    Returns:
      The updated task dict.
    """
    with _lock:
        db = _load_db()
        found = None
        for i, t in enumerate(db["tasks"]):
            if int(t.get("id")) == int(task_id):
                task = _task_from_dict(t)
                if task.completed:
                    # idempotent behavior
                    found = task
                else:
                    task.completed = True
                    task.completed_at = _now_iso()
                    db["tasks"][i] = _serialize_task(task)
                    _save_db(db)
                    found = task
                break

    if found is None:
        raise ValueError(f"task_id {task_id} not found")

    return _serialize_task(found)


# ---- Extra CRUD tools (optional but handy) ----

@mcp.tool()
def delete_task(task_id: int) -> dict[str, Any]:
    """
    Delete a task by ID.

    Returns:
      {"deleted": True, "task_id": <id>}
    """
    with _lock:
        db = _load_db()
        before = len(db["tasks"])
        db["tasks"] = [t for t in db["tasks"] if int(t.get("id")) != int(task_id)]
        after = len(db["tasks"])
        if after == before:
            raise ValueError(f"task_id {task_id} not found")
        _save_db(db)

    return {"deleted": True, "task_id": int(task_id)}


@mcp.tool()
def update_task(task_id: int, title: Optional[str] = None, due_date: Optional[str] = None) -> dict[str, Any]:
    """
    Update a task's title and/or due_date.

    Args:
      task_id: task ID
      title: new title (optional; if None, unchanged)
      due_date: new due date string (optional; if None, unchanged; if "", clears)

    Returns:
      The updated task dict.
    """
    with _lock:
        db = _load_db()
        found = None
        for i, t in enumerate(db["tasks"]):
            if int(t.get("id")) == int(task_id):
                task = _task_from_dict(t)
                if title is not None:
                    new_title = title.strip()
                    if not new_title:
                        raise ValueError("title must be non-empty when provided")
                    task.title = new_title
                if due_date is not None:
                    dd = due_date.strip() if isinstance(due_date, str) else None
                    task.due_date = dd if dd else None
                db["tasks"][i] = _serialize_task(task)
                _save_db(db)
                found = task
                break

    if found is None:
        raise ValueError(f"task_id {task_id} not found")

    return _serialize_task(found)


@mcp.tool()
def clear_completed() -> dict[str, Any]:
    """
    Remove all completed tasks.

    Returns:
      {"cleared": <count_removed>}
    """
    with _lock:
        db = _load_db()
        before = len(db["tasks"])
        db["tasks"] = [t for t in db["tasks"] if not bool(t.get("completed", False))]
        removed = before - len(db["tasks"])
        _save_db(db)

    return {"cleared": removed}

if __name__ == "__main__":
    mcp.run(transport="stdio")