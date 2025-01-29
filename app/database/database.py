from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATA_PATH
from app.database.migrations import migrate
from app.database.models import Base

DB_PATH = f"sqlite:///{DATA_PATH}/database.db"

engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False}  # Needed for SQLite in a multi-thread environment
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

migrate(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
