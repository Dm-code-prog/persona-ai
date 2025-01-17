import uuid

from sqlalchemy.orm import Session
from app.database.models import TOP5PipelineRecord


def create_pipeline_record(db: Session, script: str, volume_adjust: int, subs_color: str,
                           subs_highlight_color: str) -> TOP5PipelineRecord:
    record = TOP5PipelineRecord(
        script=script,
        volume_adjustment=volume_adjust,
        subtitle_color=subs_color,
        subtitle_highlight_color=subs_highlight_color,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_pipeline_record(db: Session, record_id: uuid.UUID) -> TOP5PipelineRecord or None:
    return db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()


def update_pipeline_record_status(db: Session, record_id: str, status: str):
    record = db.query(TOP5PipelineRecord).filter(TOP5PipelineRecord.id == record_id).first()
    record.status = status
    db.commit()
    db.refresh(record)
    return record
