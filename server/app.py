import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader


from services.shorts_pipeline.default_gpt_prompt import default_gpt_prompt
from services.shorts_pipeline.pipeline import ShortVideoPipeline

load_dotenv()

# Envs
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
pexels_api_key = os.getenv("PEXELS_API_KEY")
auth_key = os.getenv("AUTH_KEY")

# Check if API keys are provided
if not openai_api_key:
    raise ValueError("No Open API key provided.")
if not elevenlabs_api_key:
    raise ValueError("No 11labs API key provided.")
if not pexels_api_key:
    raise ValueError("No Pexels API key provided.")
if not auth_key:
    raise ValueError("No Auth key provided.")

app = FastAPI()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key == auth_key:
        return True
    # If the key is missing or invalid, raise 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )


class ConfigResponse(BaseModel):
    default_gpt_prompt: str = default_gpt_prompt


@app.get("/api/v1/pipeline/youtube/shorts/config")
async def get_pipeline(_: bool = Depends(verify_api_key)) -> ConfigResponse:
    return ConfigResponse()


class RunYoutubeShortsRequest(BaseModel):
    prompt: str = default_gpt_prompt
    elevenlabs_api_key: Optional[str] = None


@app.post("/api/v1/pipeline/youtube/shorts")
async def run_pipeline(request: RunYoutubeShortsRequest,_: bool = Depends(verify_api_key)):
    if not request.elevenlabs_api_key:
        request.elevenlabs_api_key = elevenlabs_api_key

    pipeline = ShortVideoPipeline(
        open_api_key=openai_api_key,
        elevenlaps_api_key=elevenlabs_api_key,
        pexels_api_key=pexels_api_key,
    )

    output_path = pipeline.run(request.prompt)
    return FileResponse(output_path, media_type='video/mp4', filename='output.mp4')
