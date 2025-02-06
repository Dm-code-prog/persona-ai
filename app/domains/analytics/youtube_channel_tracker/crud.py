import sqlalchemy.orm as orm

from app.database import database
from app.database.models import TrackedYouTubeChannelRecord



def create_tracked_youtube_channel(db: orm.Session, channel_id: str, channel_name: str, channel_url: str, tag: str):
    channel = TrackedYouTubeChannelRecord(
        channel_id=channel_id,
        channel_name=channel_name,
        channel_url=channel_url,
        tag=tag
    )
    
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return channel


def get_tracked_youtube_channels(db: orm.Session):
    return db.query(TrackedYouTubeChannelRecord).all()


def delete_tracked_youtube_channel(db: orm.Session, channel_id: str):
    db.query(TrackedYouTubeChannelRecord).filter(TrackedYouTubeChannelRecord.channel_id == channel_id).delete()
    db.commit()
    

def get_tracked_youtube_channel(db: orm.Session, channel_id: str):
    return db.query(TrackedYouTubeChannelRecord).filter(TrackedYouTubeChannelRecord.channel_id == channel_id).first()