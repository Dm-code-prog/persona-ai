import uuid
from typing import Optional

import sqlalchemy.orm as orm

from app.database.models import ProjectRecord, TasksRecord


def create_project(db: orm.Session,user_id: uuid.UUID, name: str) -> ProjectRecord:
    record = ProjectRecord(
        user_id=user_id,
        name=name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_projects(db: orm.Session, user_id: uuid.UUID) -> list[ProjectRecord]:
    return db.query(ProjectRecord).filter(ProjectRecord.user_id == user_id).order_by(ProjectRecord.created_at.desc()).all()


def get_project_by_id(db: orm.Session, user_id: uuid.UUID, project_id: uuid.UUID) -> ProjectRecord or None:
    return db.query(ProjectRecord).filter(ProjectRecord.user_id == user_id, ProjectRecord.id == project_id).first()


def create_task(db: orm.Session, user_id: uuid.UUID, project_id: uuid.UUID, tool_name: str, json_params: str) -> TasksRecord:
    record = TasksRecord(
        user_id=user_id,
        project_id=project_id,
        json_params=json_params,
        tool_name=tool_name
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def set_task_status(db: orm.Session, user_id: uuid.UUID, task_id: uuid.UUID, status: str,
                    error_message: Optional[str] = None) -> TasksRecord or None:
    record = db.query(TasksRecord).filter(TasksRecord.user_id == user_id, TasksRecord.id == task_id).first()
    record.status = status
    record.error_message = error_message
    db.commit()
    db.refresh(record)
    return record


def get_tasks_by_project_id(db: orm.Session, user_id: uuid.UUID, project_id: uuid.UUID) -> list[TasksRecord]:
    return db.query(TasksRecord).filter(TasksRecord.user_id == user_id, TasksRecord.project_id == project_id).order_by(
        TasksRecord.created_at.desc()).all()
