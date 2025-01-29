import uuid

from sqlalchemy.orm import Session
from app.database.models import TOP5PipelineRecord


def create_pipeline_record(db: Session, name: str) -> TOP5PipelineRecord:
    record = TOP5PipelineRecord(
        name=name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_pipeline_record(
        db: Session,
        record_id: uuid.UUID,
        script: str,
        volume_adjustment: int,
        subtitle_color: str,
        subtitle_highlight_color: str,
) -> TOP5PipelineRecord or None:
    record = db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()
    record.script = script
    record.volume_adjustment = volume_adjustment
    record.subtitle_color = subtitle_color
    record.subtitle_highlight_color = subtitle_highlight_color
    db.commit()
    db.refresh(record)
    return record


def get_pipeline_record(db: Session, record_id: uuid.UUID) -> TOP5PipelineRecord or None:
    return db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()


def get_top5_pipeline_records(db: Session):
    return db.query(TOP5PipelineRecord).all()


def update_pipeline_record_status(db: Session, record_id: str, status: str):
    record = db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()
    record.status = status
    db.commit()
    db.refresh(record)
    return record


def append_pipeline_record_logs(db: Session, record_id: str, logs: str):
    record = db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()
    record.logs += logs
    db.commit()
    db.refresh(record)
    return record
