import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware

import app.domains.secrets.endpoint as secrets
import app.domains.projects.endpoint as projects
import app.domains.tools.pause_cutter.endpoint as pause_cutter

app = fastapi.FastAPI()

# Specify the output format of the global logger

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
app.include_router(pause_cutter.router, prefix='/api/tools/pause_cutter')


@app.get('/ping')
async def ping():
    return 'pong'
