from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, Text, Float
from datetime import datetime, timezone
from .base import Base
import enum


class TaskType(str, enum.Enum):
    TREND_SCAN = "trend_scan"
    RESEARCH = "research"
    DESIGN_GENERATION = "design_generation"
    COPY_GENERATION = "copy_generation"
    LISTING_CREATION = "listing_creation"
    PUBLISH = "publish"
    METRICS_SYNC = "metrics_sync"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    celery_id = Column(String, unique=True, nullable=True)
    task_type = Column(Enum(TaskType))
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # Input
    input_data = Column(JSON, default=dict)

    # Output
    output_data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    # Cost tracking
    ai_tokens_used = Column(Integer, default=0)
    ai_cost = Column(Float, default=0.0)

    # Related entities
    product_id = Column(Integer, nullable=True)
    trend_id = Column(Integer, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "ai_cost": self.ai_cost,
            "created_at": self.created_at.isoformat(),
        }
