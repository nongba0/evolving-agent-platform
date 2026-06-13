"""
Orchestration coordinator — Stage A (Antigravity-agent driven).

ARCHITECTURE NOTE
-----------------
In this platform the *thinking* — task decomposition, child-subagent spawning,
execution, and result aggregation — is performed by the Antigravity
`evolving_companion` agent (see ../antigravity/), NOT by an external LLM API
call from this backend.

This module therefore makes **no LLM calls**. The FastAPI backend is the
persistence + observability layer: it records tasks and exposes endpoints that
the orchestrating agent (or its child subagents) use to write back logs,
checkpoints, and token-cost records so the Next.js dashboard can visualize the
autonomous run.
"""

from database import SessionLocal
from models import Task, Log


def _log(db, task_id: str, node: str, message: str, level: str = "info"):
    print(f"[{node}] {message}")
    db.add(Log(task_id=task_id, node_name=node, message=message, log_level=level))
    db.commit()


async def run_task_pipeline(task_id: str):
    """
    Register a task for agent-driven orchestration.

    No LLM is called here. The task is marked `delegated`, signaling that the
    Antigravity `evolving_companion` orchestrator should pick it up, decompose
    it, spawn child subagents, and report progress back through the /api
    endpoints (logs, costs, status).
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = "delegated"
        db.commit()

        _log(
            db,
            task_id,
            "Orchestrator",
            "Task delegated to the Antigravity 'evolving_companion' agent for "
            "autonomous decomposition and subagent orchestration. "
            "No backend LLM call is made; the agent reports progress, cost, and "
            "status back through the /api endpoints.",
        )
    finally:
        db.commit()
        db.close()
