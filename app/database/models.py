import uuid

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TOP5PipelineRecord(Base):
    __tablename__ = 'top5_pipelines'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    script = Column(String)
    status = Column(String, default="created")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    subtitle_color = Column(String)
    subtitle_highlight_color = Column(String)

    volume_adjustment = Column(Integer)

