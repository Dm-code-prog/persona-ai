import logging
import os
import jwt

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import app.domains.secrets.endpoint as secrets
import app.domains.projects.endpoint as projects
import app.domains.tools.pause_cutter.endpoint as pause_cutter
import app.domains.tools.video_unifier.endpoint as video_unifier
import app.domains.analytics.youtube_channel_tracker.endpoint as youtube_channel_tracker

app = fastapi.FastAPI()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

origins = [
    "https://persona-ui-iota.vercel.app",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(secrets.router, prefix='/api/secrets')
app.include_router(projects.router, prefix='/api/projects')
app.include_router(youtube_channel_tracker.router, prefix='/api/analytics/youtube_channel_tracker')

app.include_router(pause_cutter.router, prefix='/api/tools/pause_cutter')
app.include_router(video_unifier.router, prefix='/api/tools/video_unifier')

@app.get('/ping')
async def ping():
    return 'pong'
