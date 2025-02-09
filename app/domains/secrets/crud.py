from sqlalchemy.orm import Session
import uuid
from app.database.models import SecretRecord


def set_secret(db: Session, user_id: uuid.UUID, key:str, value:str):
    record = SecretRecord(
        user_id=user_id,
        key=key,
        value=value
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_secret(db: Session, user_id: uuid.UUID, key: str) -> SecretRecord or None:
    return db.query(SecretRecord).filter(SecretRecord.user_id==user_id, SecretRecord.key==key).first()