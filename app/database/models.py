import uuid

from sqlalchemy import Column, Integer, String, DateTime, func, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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


class TrackedYouTubeChannelRecord(Base):
    __tablename__ = 'analytics_tracked_youtube_channels'

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String)
    channel_name = Column(String)
    channel_url = Column(String)
    
    tag = Column(String)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
