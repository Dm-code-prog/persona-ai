import fastapi
import pydantic
import os
import sqlalchemy.orm as orm
import datetime
import requests
import httpx
import app.domains.analytics.youtube_channel_tracker.crud as crud
import app.domains.secrets.crud as secret_crud
from app.database import database
from app.auth import get_current_user
from app.config import FRONT_END_URL
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# -------------------------------------------------------------------
# Configuration for Google OAuth (assumed to be stored in env vars)
# -------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not REDIRECT_URI:
    raise fastapi.HTTPException(status_code=400, detail="Google OAuth configuration is missing")

# The scopes you need for your app.
SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly"
]

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
async def create_tracked_youtube_channel(
    channel: CreateTrackedYoutubeChannel,
    db: orm.Session = fastapi.Depends(database.get_db),
    user: dict = fastapi.Depends(get_current_user)
):
    youtube_data_api_key = secret_crud.get_secret(db, user['sub'], "youtube_data_api_key")
    if not youtube_data_api_key:
        raise fastapi.HTTPException(status_code=400, detail="YouTube data API key not found")
    
    handle = channel.channel_url.split("/")[-1]
    id, name = get_channel_info_from_handle(handle, youtube_data_api_key.value)
    
    if id == "Not found":
        raise fastapi.HTTPException(status_code=400, detail="Channel not found")
    if name == "Not found":
        raise fastapi.HTTPException(status_code=400, detail="Channel not found")
    

    exists = crud.get_tracked_youtube_channel(db, user['sub'], id)
    if exists:
        raise fastapi.HTTPException(status_code=400, detail="Channel already tracked")
    
    channel = crud.create_tracked_youtube_channel(
        db=db,
        user_id=user['sub'],
        channel_id=id,
        channel_name=name,
        channel_url=channel.channel_url,
        tag=channel.tag
        )
    
    return channel
    
    

@router.get('/list', tags=['Analytics'], response_model=list[TrackedYoutubeChannel])
async def get_tracked_youtube_channels(db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    channels = crud.get_tracked_youtube_channels(db, user['sub'])
    return channels


@router.delete('/{channel_id}', tags=['Analytics'])
async def delete_tracked_youtube_channel(channel_id: str, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    crud.delete_tracked_youtube_channel(db, user['sub'], channel_id)
    return {"message": "Channel deleted successfully"}


@router.get('/{channel_id}', tags=['Analytics'], response_model=TrackedYoutubeChannel)
async def get_tracked_youtube_channel(channel_id: str, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    channel = crud.get_tracked_youtube_channel(db, user['sub'], channel_id)
    return channel

def get_channel_info_from_handle(handle: str, api_key: str):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=id,snippet&forHandle={handle}&key={api_key}"
    response = requests.get(url).json()
    id = response.get("items", [{}])[0].get("id", "Not found")
    name = response.get("items", [{}])[0].get("snippet", {}).get("title", "Not found")
    return id, name

@router.get("/{channel_id}/analytics", tags=["Analytics"])
async def get_youtube_analytics(
    channel_id: str,
    startDate: str,
    endDate: str,
    db: orm.Session = fastapi.Depends(database.get_db),
    user: dict = fastapi.Depends(get_current_user)
):    
    # Look up the tracked channel record for the authenticated user.
    channel_record = crud.get_tracked_youtube_channel(db, user["sub"], channel_id)
    if not channel_record:
        raise fastapi.HTTPException(status_code=404, detail="Channel not tracked")

    # Check that the tokens are present.
    if not channel_record.access_token or not channel_record.refresh_token:
        raise fastapi.HTTPException(status_code=401, detail="Missing OAuth tokens. Please authorize the channel first.")

    # Ensure we have a valid (or refreshed) access token.
    try:
        access_token = get_valid_access_token(db, channel_record)
    except fastapi.HTTPException as e:
        raise fastapi.HTTPException(status_code=401, detail=str(e.detail))

    # Build the YouTube Analytics API URL and query parameters.
    analytics_url = "https://youtubeanalytics.googleapis.com/v2/reports"
    params = {
        "ids": f"channel=={channel_id}",
        "startDate": startDate,
        "endDate": endDate,
        "dimensions": "day",
        "metrics": "views,estimatedMinutesWatched,subscribersGained,likes,dislikes,averageViewDuration,averageViewPercentage",
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(analytics_url, params=params, headers=headers)

    if response.status_code == 401:
        # Possibly the token is invalid or expired.
        raise fastapi.HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token")
    elif not response.status_code == 200:
        raise fastapi.HTTPException(status_code=response.status_code, detail="Failed to retrieve analytics data")

    # Return the JSON response as received from the YouTube Analytics API.
    return response.json()

# -------------------------------------------------------------------
# New endpoints to handle OAuth: initiating the flow and processing the callback
# -------------------------------------------------------------------

@router.get("/{channel_id}/auth", tags=["Authorization"])
def youtube_auth_start(
    channel_id: str,
    db: orm.Session = fastapi.Depends(database.get_db),
    user: dict = fastapi.Depends(get_current_user)
):
    """
    Initiates the Google OAuth flow for a specific tracked YouTube channel.
    Expects the client to pass the channel_id (that was previously created/tracked).
    """
    # Ensure the channel exists for this user.
    channel = crud.get_tracked_youtube_channel(db, user['sub'], channel_id)
    if not channel:
        raise fastapi.HTTPException(status_code=404, detail="Channel not found")
    
    # Create a state parameter (e.g. "user_id:channel_id") for later verification.
    state = f"{user['sub']}:{channel_id}"
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
    # Request offline access to get a refresh token.
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        state=state,
        prompt="consent"
    )
    # Redirect the client to Google's OAuth consent page.
    return {
        "authorization_url": authorization_url
    }


@router.get("/auth/callback", tags=["Authorization"])
def youtube_auth_callback(
    code: str,
    state: str,
    db: orm.Session = fastapi.Depends(database.get_db)
):
    """
    OAuth callback endpoint. Exchanges the code for tokens and updates the tracked channel.
    """
    # Expect the state in the format "user_id:channel_id"
    try:
        user_id, channel_id = state.split(":", 1)
    except Exception:
        raise fastapi.HTTPException(status_code=400, detail="Invalid state parameter")
    
        
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
        
    # Extract tokens and expiry timestamp.
    access_token = credentials.token
    refresh_token = credentials.refresh_token
    token_expires_at = credentials.expiry
    
    # Update the tracked channel record.
    channel_record = crud.get_tracked_youtube_channel(db, user_id, channel_id)
    if not channel_record:
        raise fastapi.HTTPException(status_code=404, detail="Channel record not found")
    
    channel_record.access_token = access_token
    channel_record.refresh_token = refresh_token
    channel_record.token_expires_at = token_expires_at
    db.commit()
    db.refresh(channel_record)
    
    return fastapi.responses.RedirectResponse(url=f"{FRONT_END_URL}/analytics/youtube-channels")

# -------------------------------------------------------------------
# Helper function: Refresh token on-demand (for use in endpoints that access YouTube)
# -------------------------------------------------------------------
def get_valid_access_token(db: orm.Session, channel_record) -> str:
    """
    Checks if the access token is expired and, if so, refreshes it.
    Returns a valid access token.
    """
    from datetime import datetime
    # If token_expires_at is set and is in the past, refresh it.
    if channel_record.token_expires_at and channel_record.token_expires_at < datetime.utcnow():
        creds = Credentials(
            token=channel_record.access_token,
            refresh_token=channel_record.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )
        # Create a request object required by google-auth to refresh credentials.
        req = Request()
        try:
            creds.refresh(req)
        except Exception as e:
            raise fastapi.HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")
        
        # Update the channel record with the refreshed token and expiry.
        channel_record.access_token = creds.token
        channel_record.token_expires_at = creds.expiry
        db.commit()
    
    return channel_record.access_token