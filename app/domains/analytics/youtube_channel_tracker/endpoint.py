import fastapi
import pydantic
import sqlalchemy.orm as orm
import datetime
import pytube
import requests
import app.domains.analytics.youtube_channel_tracker.crud as crud
import app.domains.secrets.crud as secret_crud
from app.database import database

router = fastapi.APIRouter()

class CreateTrackedYoutubeChannel(pydantic.BaseModel):
    channel_url: str
    tag: str

class TrackedYoutubeChannel(pydantic.BaseModel):
    channel_id: str
    channel_name: str
    channel_url: str
    tag: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@router.post('/', tags=['Analytics' ], response_model=TrackedYoutubeChannel)
async def create_tracked_youtube_channel(channel: CreateTrackedYoutubeChannel, db: orm.Session = fastapi.Depends(database.get_db)):
    youtube_data_api_key = secret_crud.get_secret(db, "youtube_data_api_key")
    if not youtube_data_api_key:
        raise fastapi.HTTPException(status_code=400, detail="YouTube data API key not found")
    
    handle = channel.channel_url.split("/")[-1]
    id, name = get_channel_info_from_handle(handle, youtube_data_api_key.value)
    
    if id == "Not found":
        raise fastapi.HTTPException(status_code=400, detail="Channel not found")
    if name == "Not found":
        raise fastapi.HTTPException(status_code=400, detail="Channel not found")
    

    exists = crud.get_tracked_youtube_channel(db, id)
    if exists:
        raise fastapi.HTTPException(status_code=400, detail="Channel already tracked")
    
    channel = crud.create_tracked_youtube_channel(
        db=db,
        channel_id=id,
        channel_name=name,
        channel_url=channel.channel_url,
        tag=channel.tag
        )
    
    return channel
    
    

@router.get('/list', tags=['Analytics'], response_model=list[TrackedYoutubeChannel])
async def get_tracked_youtube_channels(db: orm.Session = fastapi.Depends(database.get_db)):
    channels = crud.get_tracked_youtube_channels(db)
    return channels


@router.delete('/{channel_id}', tags=['Analytics'])
async def delete_tracked_youtube_channel(channel_id: str, db: orm.Session = fastapi.Depends(database.get_db)):
    crud.delete_tracked_youtube_channel(db, channel_id)
    return {"message": "Channel deleted successfully"}


@router.get('/{channel_id}', tags=['Analytics'], response_model=TrackedYoutubeChannel)
async def get_tracked_youtube_channel(channel_id: str, db: orm.Session = fastapi.Depends(database.get_db)):
    channel = crud.get_tracked_youtube_channel(db, channel_id)
    return channel

def get_channel_info_from_handle(handle: str, api_key: str):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=id,snippet&forHandle={handle}&key={api_key}"
    response = requests.get(url).json()
    id = response.get("items", [{}])[0].get("id", "Not found")
    name = response.get("items", [{}])[0].get("snippet", {}).get("title", "Not found")
    return id, name