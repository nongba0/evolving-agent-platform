from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    system_active = Column(Boolean, default=True)
    learning_active = Column(Boolean, default=True)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, running, paused, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    checkpoints = relationship("Checkpoint", back_populates="task", cascade="all, delete-orphan")
    token_costs = relationship("TokenCost", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="task", cascade="all, delete-orphan")

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    node_name = Column(String, nullable=False)
    state_data = Column(Text, nullable=False)  # Serialized JSON of states
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="checkpoints")

class TokenCost(Base):
    __tablename__ = "token_costs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    node_name = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="token_costs")

class Log(Base):
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    node_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    log_level = Column(String, default="info")
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="logs")
