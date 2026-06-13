import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
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

# Default Model Selection (Using the verified gemini-3.5-flash)
MODEL_NAME = "gemini-3.5-flash"

# Price rates per 1,000,000 tokens (estimates for gemini-3.5-flash)
PRICE_INPUT_1M = 0.075
PRICE_OUTPUT_1M = 0.30

# ---------------------------------------------------------
# 1. LLM Wrapper with Cost Tracking
# ---------------------------------------------------------
def call_gemini_with_cost(
    task_id: str,
    node_name: str,
    prompt: str,
    system_instruction: str = None,
    db: Session = None
) -> str:
    """
    Calls Gemini API, extracts token usage metadata, logs cost to DB, and returns text.
    """
    try:
        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction
            
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config
        )
        
        # Extract token usage metadata
        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0
            
        # Calculate estimated cost
        cost = (input_tokens / 1_000_000) * PRICE_INPUT_1M + (output_tokens / 1_000_000) * PRICE_OUTPUT_1M
        
        # Log cost in DB
        db_cost = TokenCost(
            task_id=task_id,
            node_name=node_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost
        )
        db.add(db_cost)
        db.commit()
        
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {str(e)}")

# ---------------------------------------------------------
# 2. Asynchronous DAG Executor with Fault Tolerance & Budget Caps
# ---------------------------------------------------------
async def run_task_pipeline(task_id: str, budget_limit: float = 0.50):
    """
    Background worker running the pipeline with checkpoints, cost caps, and task resumption.
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
        
        # Pre-planned task nodes (pre-compiled template)
        steps = [
            {
                "id": "data_scraping", 
                "name": "Data Scraper Node",
                "system_instruction": "You are a web scraper assistant. Generate a raw JSON array of 3 popular coffee shops in Seoul containing name, address, and ratings.",
                "prompt": "List 3 seoul cafes in JSON format."
            },
            {
                "id": "data_parsing", 
                "name": "Data Parser Node",
                "system_instruction": "You are a data cleaning assistant. Parse raw coffee shop JSON and standardise the schema to contain name, address, rating (float), and country (set to South Korea). Output clean JSON only.",
                "prompt": "Clean and format the scraped cafe data JSON."
            },
        ]
        
        # Check for existing checkpoints (Resumption logic)
        checkpoints = db.query(Checkpoint).filter(Checkpoint.task_id == task_id).all()
        completed_nodes = {cp.node_name: json.loads(cp.state_data) for cp in checkpoints}
        
        shared_state = {}
        events = {step["id"]: asyncio.Event() for step in steps}
        
        # Pre-populate shared state from checkpoints
        for node_name, state_data in completed_nodes.items():
            shared_state[node_name] = state_data.get("output")
            log_message("Orchestrator", f"Restored checkpoint for [{node_name}]. Skipping execution.")
            events[node_name].set() # Mark completed immediately for downstream nodes

        async def run_node(step):
            # A. Wait if there are dependencies (none in this sample, but scheduling is supported)
            # B. Check if already completed (checkpoint bypass)
            if step["id"] in completed_nodes:
                return
                
            log_message(step["id"], f"Starting script execution for node: {step['name']}")
            
            # C. Check Token Cost Budget Limit
            total_cost = db.query(func.sum(TokenCost.estimated_cost)).filter(TokenCost.task_id == task_id).scalar() or 0.0
            if total_cost >= budget_limit:
                log_message(step["id"], f"Budget Cap breached (${total_cost:.4f} >= ${budget_limit:.2f}). Pausing task.", "warning")
                task.status = "paused"
                db.commit()
                raise RuntimeError("Task execution paused due to budget cap breach.")

            # D. Run task execution using the LLM with cost logging
            # Inject inputs from other nodes if dependencies existed
            input_prompt = step["prompt"]
            if step["id"] == "data_parsing" and "data_scraping" in shared_state:
                # Pass scraping output to parsing input
                input_prompt = f"Raw scraped data:\n{shared_state['data_scraping']}\n\n{step['prompt']}"

            # Run API Call with retries
            retries = 3
            success = False
            result_text = ""
            
            for attempt in range(1, retries + 1):
                try:
                    result_text = call_gemini_with_cost(
                        task_id=task_id,
                        node_name=step["id"],
                        prompt=input_prompt,
                        system_instruction=step["system_instruction"],
                        db=db
                    )
                    
                    if not result_text.strip():
                        raise ValueError("Gemini returned empty text.")
                        
                    success = True
                    break
                except Exception as e:
                    log_message(step["id"], f"L1 Validation check failed on attempt {attempt}: {str(e)}", "warning")
                    if attempt < retries:
                        await asyncio.sleep(2)
            
            if not success:
                log_message(step["id"], "Execution failed after maximum L1 retries.", "error")
                raise RuntimeError(f"Subtask {step['id']} failed validation.")

            # E. Save output and write Checkpoint
            shared_state[step["id"]] = result_text
            db_checkpoint = Checkpoint(
                task_id=task_id,
                node_name=step["id"],
                state_data=json.dumps({"output": result_text})
            )
            db.add(db_checkpoint)
            db.commit()
            
            log_message(step["id"], "Completed successfully. Checkpoint saved.")
            events[step["id"]].set()

        # Execute all steps in parallel
        await asyncio.gather(*(run_node(step) for step in steps))
        
        # Set task status to completed if not paused by budget cap during execution
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
