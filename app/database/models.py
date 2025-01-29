import uuid

from sqlalchemy import Column, Integer, String, DateTime, func, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TOP5PipelineRecord(Base):
    __tablename__ = 'top5_pipelines'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    script = Column(String)
    status = Column(String, default="created")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    subtitle_color = Column(String)
    subtitle_highlight_color = Column(String)

    volume_adjustment = Column(Integer)

    logs = Column(String)


class ProjectRecord(Base):
    __tablename__ = 'projects'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, unique=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TasksRecord(Base):
    __tablename__ = 'tasks'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    project_id = Column(UUID)
    tool_name = Column(String)
    status = Column(String, default="created")
    json_params = Column(String)
    error_message = Column(String)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SecretRecord(Base):
    __tablename__ = 'secrets'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String)
    value = Column(String)
