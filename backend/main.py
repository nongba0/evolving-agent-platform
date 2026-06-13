from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import engine, Base, get_db
from models import Settings, Task, Log, TokenCost
from schemas import (
    SettingsBase, SettingsResponse,
    TaskCreate, TaskResponse, TaskStatusUpdate,
    LogResponse, LogCreate,
    TokenCostResponse, TokenCostCreate
)
from orchestrator import run_task_pipeline

# Initialize SQLite tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Self-Evolving Multi-Agent Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to seed default settings
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        # Check if settings exist, if not seed it
        settings = db.query(Settings).first()
        if not settings:
            db_settings = Settings(id=1, system_active=True, learning_active=True)
            db.add(db_settings)
            db.commit()
    finally:
        db.close()

@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@app.post("/api/settings", response_model=SettingsResponse)
def update_settings(settings_data: SettingsBase, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(id=1)
        db.add(settings)
    settings.system_active = settings_data.system_active
    settings.learning_active = settings_data.learning_active
    db.commit()
    db.refresh(settings)
    return settings

@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(task_data: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check if system is active (ON/OFF control)
    settings = db.query(Settings).first()
    if settings and not settings.system_active:
        raise HTTPException(
            status_code=503,
            detail="System is currently suspended (OFF). Toggle System active ON to run tasks."
        )
        
    task_id = str(uuid.uuid4())
    db_task = Task(id=task_id, prompt=task_data.prompt, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Trigger background execution pipeline asynchronously
    background_tasks.add_task(run_task_pipeline, task_id)
    
    return db_task

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/{task_id}/resume", response_model=TaskResponse)
def resume_task(task_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check if system is active
    settings = db.query(Settings).first()
    if settings and not settings.system_active:
        raise HTTPException(
            status_code=503,
            detail="System is currently suspended (OFF). Toggle System active ON to resume tasks."
        )
        
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in ["failed", "paused", "completed"]:
        raise HTTPException(status_code=400, detail=f"Cannot resume a task in '{task.status}' status")
        
    task.status = "pending"
    db.commit()
    db.refresh(task)
    
    # Trigger execution (resuming from checkpoints)
    background_tasks.add_task(run_task_pipeline, task_id)
    
    return task

@app.get("/api/tasks/{task_id}/logs", response_model=List[LogResponse])
def get_task_logs(task_id: str, db: Session = Depends(get_db)):
    logs = db.query(Log).filter(Log.task_id == task_id).order_by(Log.timestamp.asc()).all()
    return logs

@app.get("/api/tasks/{task_id}/costs", response_model=List[TokenCostResponse])
def get_task_costs(task_id: str, db: Session = Depends(get_db)):
    costs = db.query(TokenCost).filter(TokenCost.task_id == task_id).order_by(TokenCost.timestamp.asc()).all()
    return costs

# ---------------------------------------------------------------------------
# Agent write-back endpoints
# The Antigravity 'evolving_companion' orchestrator (and its child subagents)
# report progress, status, and cost here so the dashboard reflects the run.
# ---------------------------------------------------------------------------
def _require_task(task_id: str, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/{task_id}/status", response_model=TaskResponse)
def set_task_status(task_id: str, body: TaskStatusUpdate, db: Session = Depends(get_db)):
    task = _require_task(task_id, db)
    task.status = body.status
    db.commit()
    db.refresh(task)
    return task

@app.post("/api/tasks/{task_id}/logs", response_model=LogResponse, status_code=201)
def add_task_log(task_id: str, body: LogCreate, db: Session = Depends(get_db)):
    _require_task(task_id, db)
    log = Log(task_id=task_id, node_name=body.node_name, message=body.message, log_level=body.log_level)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

@app.post("/api/tasks/{task_id}/costs", response_model=TokenCostResponse, status_code=201)
def add_task_cost(task_id: str, body: TokenCostCreate, db: Session = Depends(get_db)):
    _require_task(task_id, db)
    cost = TokenCost(
        task_id=task_id,
        node_name=body.node_name,
        input_tokens=body.input_tokens,
        output_tokens=body.output_tokens,
        estimated_cost=body.estimated_cost,
    )
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost
