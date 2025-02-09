from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base

import os

from dotenv import load_dotenv

load_dotenv() 

DB_DSN = os.getenv("DB_DSN") 

if not DB_DSN:
    raise ValueError("DB_DSN is not set")

engine = create_engine(
    DB_DSN,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
