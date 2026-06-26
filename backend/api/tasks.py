from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.base import get_db
from models.task import Task, TaskStatus, TaskType
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/")
def list_tasks(
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """List tasks"""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if task_type:
        query = query.filter(Task.task_type == task_type)

    tasks = query.order_by(Task.created_at.desc()).limit(limit).all()

    return [t.to_dict() for t in tasks]


@router.get("/summary")
def get_task_summary(db: Session = Depends(get_db)):
    """Get task counts by type and status"""
    from sqlalchemy import func

    summary = db.query(
        Task.task_type,
        Task.status,
        func.count(Task.id).label('count')
    ).group_by(
        Task.task_type,
        Task.status
    ).all()

    result = {}
    for task_type, status, count in summary:
        tt = task_type.value if task_type else "unknown"
        if tt not in result:
            result[tt] = {}
        result[tt][status.value] = count

    return result


@router.get("/recent-errors")
def get_recent_errors(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent failed tasks"""
    errors = db.query(Task).filter(
        Task.status == TaskStatus.FAILED,
        Task.error_message != None
    ).order_by(Task.created_at.desc()).limit(limit).all()

    return [t.to_dict() for t in errors]
