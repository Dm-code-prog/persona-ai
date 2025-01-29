from sqlalchemy.orm import Session

from app.database.models import SecretRecord


def set_secret(db: Session, key:str, value:str):
    record = SecretRecord(
        key=key,
        value=value
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_secret(db: Session, key: str) -> SecretRecord or None:
    return db.query(SecretRecord).filter(SecretRecord.key==key).first()