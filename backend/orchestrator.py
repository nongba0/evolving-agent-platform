import asyncio
import json
import os
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv

from database import SessionLocal
from models import Task, Checkpoint, TokenCost, Log

load_dotenv()

# Initialize GenAI Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()

# Model selection (override with GEMINI_MODEL env var if the default is unavailable)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Price rates per 1,000,000 tokens (estimates for gemini-3.5-flash)
PRICE_INPUT_1M = 0.075
PRICE_OUTPUT_1M = 0.30

# Orchestration constants
PLANNER_NODE = "__planner__"   # reserved node name for the planning phase / plan checkpoint
MAX_STEPS = 5                  # safety cap on dynamic task decomposition

PLANNER_SYSTEM = (
    "You are an orchestration planner for a self-evolving multi-agent system.\n"
    f"Break the user's task into an ordered list of 1 to {MAX_STEPS} concrete sub-tasks.\n"
    "Each sub-task is run by a worker agent in order; later workers receive the outputs of earlier ones.\n"
    "Respond with ONLY a raw JSON array (no markdown fences, no prose). Each element must be:\n"
    '{"id": "snake_case_id", "name": "Human Readable Name", '
    '"instruction": "precise system instruction telling the worker exactly what to produce"}\n'
    "Keep the plan minimal and non-redundant. Prefer fewer, higher-quality steps."
)

# ---------------------------------------------------------
# 1. LLM Wrapper with Cost Tracking
# ---------------------------------------------------------
def _invoke_gemini(prompt: str, system_instruction: Optional[str] = None) -> Tuple[str, int, int]:
    """
    Blocking Gemini network call. Returns (text, input_tokens, output_tokens).
    Pure I/O with no DB access, so it is safe to offload to a worker thread.
    """
    config = types.GenerateContentConfig()
    if system_instruction:
        config.system_instruction = system_instruction

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=config,
    )

    input_tokens = 0
    output_tokens = 0
    if response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    return (response.text or "").strip(), input_tokens, output_tokens


async def call_gemini_with_cost(
    task_id: str,
    node_name: str,
    prompt: str,
    system_instruction: str = None,
    db: Session = None,
) -> str:
    """
    Calls Gemini off the event loop (so the API server never freezes during a request),
    then logs token usage / estimated cost to the DB on the loop thread, and returns text.

    NOTE: This is the ONLY sanctioned entry point for LLM calls (cost tracking is guaranteed here).
    """
    try:
        # Offload the blocking network call to a thread; the event loop stays responsive
        # and other async work (including parallel nodes) is no longer serialized behind it.
        text, input_tokens, output_tokens = await asyncio.to_thread(
            _invoke_gemini, prompt, system_instruction
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {str(e)}")

    # Calculate estimated cost
    cost = (input_tokens / 1_000_000) * PRICE_INPUT_1M + (output_tokens / 1_000_000) * PRICE_OUTPUT_1M

    # Log cost in DB (on the event loop thread — single session stays safe)
    db_cost = TokenCost(
        task_id=task_id,
        node_name=node_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=cost,
    )
    db.add(db_cost)
    db.commit()

    return text


# ---------------------------------------------------------
# 2. Dynamic Planner — decompose the user's prompt into sub-tasks
# ---------------------------------------------------------
def _parse_plan(raw: str) -> List[Dict[str, str]]:
    """Extract and normalize the JSON plan from the planner's raw response."""
    cleaned = raw.strip()
    # Tolerate markdown fences or surrounding prose by grabbing the first [...] block.
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    steps_raw = json.loads(cleaned)
    normalized: List[Dict[str, str]] = []
    for i, s in enumerate(steps_raw[:MAX_STEPS], start=1):
        if not isinstance(s, dict):
            continue
        instruction = str(s.get("instruction") or "").strip()
        if not instruction:
            continue
        sid = str(s.get("id") or f"step_{i}").strip().replace(" ", "_") or f"step_{i}"
        name = str(s.get("name") or f"Step {i}").strip()
        normalized.append({"id": sid, "name": name, "instruction": instruction})

    # Guarantee unique node ids (checkpoints key on node_name)
    seen: Dict[str, int] = {}
    for s in normalized:
        base = s["id"]
        if base in seen:
            seen[base] += 1
            s["id"] = f"{base}_{seen[base]}"
        else:
            seen[base] = 0
    return normalized


async def plan_steps(task_id: str, prompt: str, db: Session, log_message) -> List[Dict[str, str]]:
    """Use the LLM to turn the user's prompt into an ordered list of worker sub-tasks."""
    planner_prompt = f"User task:\n{prompt}\n\nProduce the JSON plan now."
    raw = await call_gemini_with_cost(task_id, PLANNER_NODE, planner_prompt, PLANNER_SYSTEM, db)

    try:
        steps = _parse_plan(raw)
    except Exception as e:
        log_message(PLANNER_NODE, f"Plan parsing failed ({e}); falling back to a single generic step.", "warning")
        steps = []

    if not steps:
        steps = [{
            "id": "execute",
            "name": "Execute Task",
            "instruction": "Complete the user's task directly and return the final result.",
        }]
    return steps


# ---------------------------------------------------------
# 3. Asynchronous Pipeline with Fault Tolerance & Budget Caps
# ---------------------------------------------------------
async def run_task_pipeline(task_id: str, budget_limit: float = 0.50):
    """
    Background worker running the pipeline with a dynamic (prompt-driven) plan,
    checkpoints, cost caps, and task resumption.
    """
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        return

    task.status = "running"
    db.commit()

    def log_message(node: str, msg: str, level: str = "info"):
        print(f"[{node}] {msg}")
        db_log = Log(task_id=task_id, node_name=node, message=msg, log_level=level)
        db.add(db_log)
        db.commit()

    try:
        log_message("Orchestrator", f"Initializing task pipeline: {task_id}")

        # Load existing checkpoints (resumption logic)
        checkpoints = db.query(Checkpoint).filter(Checkpoint.task_id == task_id).all()
        cp_map = {cp.node_name: json.loads(cp.state_data) for cp in checkpoints}

        # --- Phase A: PLAN (reuse the persisted plan on resume for stable checkpoint matching) ---
        if PLANNER_NODE in cp_map:
            steps = cp_map[PLANNER_NODE].get("plan", [])
            log_message("Orchestrator", f"Restored existing plan with {len(steps)} step(s).")
        else:
            log_message("Orchestrator", "Analyzing prompt and generating a dynamic plan...")
            steps = await plan_steps(task_id, task.prompt, db, log_message)
            db.add(Checkpoint(
                task_id=task_id,
                node_name=PLANNER_NODE,
                state_data=json.dumps({"plan": steps}),
            ))
            db.commit()
            plan_summary = " -> ".join(s["id"] for s in steps)
            log_message("Orchestrator", f"Plan generated ({len(steps)} step(s)): {plan_summary}")

        # Pre-populate shared state from completed step checkpoints
        shared_state: Dict[str, str] = {}
        for node_name, state in cp_map.items():
            if node_name == PLANNER_NODE:
                continue
            shared_state[node_name] = state.get("output")
            log_message("Orchestrator", f"Restored checkpoint for [{node_name}]. Will skip execution.")

        # --- Phase B: EXECUTE steps in order, feeding prior outputs forward ---
        for idx, step in enumerate(steps):
            sid = step["id"]

            # Skip if already completed (checkpoint bypass)
            if sid in shared_state:
                continue

            # Token cost budget limit check (before each step)
            total_cost = db.query(func.sum(TokenCost.estimated_cost)).filter(
                TokenCost.task_id == task_id
            ).scalar() or 0.0
            if total_cost >= budget_limit:
                log_message(sid, f"Budget Cap breached (${total_cost:.4f} >= ${budget_limit:.2f}). Pausing task.", "warning")
                task.status = "paused"
                db.commit()
                raise RuntimeError("Task execution paused due to budget cap breach.")

            log_message(sid, f"Starting node: {step['name']}")

            # Build the worker input: original task + outputs of all prior steps (context chain)
            context_parts = [f"Original task: {task.prompt}"]
            for prev in steps[:idx]:
                prev_out = shared_state.get(prev["id"])
                if prev_out:
                    context_parts.append(f"Output of [{prev['name']}]:\n{prev_out}")
            input_prompt = "\n\n".join(context_parts) + f"\n\nNow perform this step: {step['name']}"

            # L1 micro-validation with retries
            retries = 3
            result_text = ""
            success = False
            for attempt in range(1, retries + 1):
                try:
                    result_text = await call_gemini_with_cost(
                        task_id=task_id,
                        node_name=sid,
                        prompt=input_prompt,
                        system_instruction=step["instruction"],
                        db=db,
                    )
                    if not result_text.strip():
                        raise ValueError("Gemini returned empty text.")
                    success = True
                    break
                except Exception as e:
                    log_message(sid, f"L1 validation check failed on attempt {attempt}: {str(e)}", "warning")
                    if attempt < retries:
                        await asyncio.sleep(2)

            if not success:
                log_message(sid, "Execution failed after maximum L1 retries.", "error")
                raise RuntimeError(f"Subtask {sid} failed validation.")

            # Save output and write checkpoint
            shared_state[sid] = result_text
            db.add(Checkpoint(
                task_id=task_id,
                node_name=sid,
                state_data=json.dumps({"output": result_text}),
            ))
            db.commit()
            log_message(sid, "Completed successfully. Checkpoint saved.")

        # Mark completed if not paused by a budget cap during execution
        db.refresh(task)
        if task.status == "running":
            task.status = "completed"
            log_message("Orchestrator", "Task pipeline completed successfully.")

    except Exception as e:
        db.refresh(task)
        if task.status != "paused":
            task.status = "failed"
            log_message("Orchestrator", f"Pipeline failed: {str(e)}", "error")
    finally:
        db.commit()
        db.close()
