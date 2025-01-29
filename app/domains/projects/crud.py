import uuid
from typing import Optional

import sqlalchemy.orm as orm

from app.database.models import ProjectRecord, TasksRecord


def create_project(db: orm.Session, name: str) -> ProjectRecord:
    record = ProjectRecord(
        name=name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_projects(db: orm.Session) -> [ProjectRecord]:
    return db.query(ProjectRecord).all()


def get_project_by_id(db: orm.Session, project_id: uuid.UUID) -> ProjectRecord or None:
    return db.query(ProjectRecord).filter(ProjectRecord.id == project_id).first()


def create_task(db: orm.Session, project_id: uuid.UUID, tool_name: str, json_params: str) -> TasksRecord:
    record = TasksRecord(
        project_id=project_id,
        json_params=json_params,
        tool_name=tool_name
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def set_task_status(db: orm.Session, task_id: uuid.UUID, status: str,
                    error_message: Optional[str] = None) -> TasksRecord or None:
    record = db.query(TasksRecord).filter(TasksRecord.id == task_id).first()
    record.status = status
    record.error_message = error_message
    db.commit()
    db.refresh(record)
    return record


def get_tasks_by_project_id(db: orm.Session, project_id: uuid.UUID) -> [TasksRecord]:
    return db.query(TasksRecord).filter(TasksRecord.project_id == project_id).order_by(
        TasksRecord.created_at.desc()).all()
