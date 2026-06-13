from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class SettingsBase(BaseModel):
    system_active: bool
    learning_active: bool

class SettingsResponse(SettingsBase):
    id: int

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    prompt: str

class TaskResponse(BaseModel):
    id: str
    prompt: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LogResponse(BaseModel):
    id: int
    task_id: str
    node_name: str
    message: str
    log_level: str
    timestamp: datetime

    class Config:
        from_attributes = True

class TokenCostResponse(BaseModel):
    id: int
    task_id: str
    node_name: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    timestamp: datetime

    class Config:
        from_attributes = True
