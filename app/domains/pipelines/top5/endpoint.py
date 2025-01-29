import datetime
import logging
import os
import threading
import uuid
from typing import Optional

import fastapi
import fastapi.responses as responses
import queue
import pydantic

import sqlalchemy.orm as orm
from fastapi import HTTPException

import app.domains.pipelines.top5.crud as crud
import app.domains.secrets.crud as secrets_crud
import app.database.database as database
from app.config import MEDIA_PATH

import services.pipelines.top5_generator.pipeline as pipeline

router = fastapi.APIRouter()


class InitRequest(pydantic.BaseModel):
    name: str


class InitResponse(pydantic.BaseModel):
    id: uuid.UUID
    status: str


@router.post('/init', response_model=InitResponse)
async def init_top5_pipeline(request: InitRequest, db: orm.Session = fastapi.Depends(database.get_db)):
    try:
        record = crud.create_pipeline_record(
            db,
            name=request.name,
        )

        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id)))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input'))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input', 'videos'))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input', 'photos'))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input', 'sound_effects'))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input', 'video_effects'))
        os.makedirs(os.path.join(MEDIA_PATH, 'pipelines', 'top5', str(record.id), 'input', 'music'))

        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'output'))
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))

    return {
        'id': record.id,
        'status': record.status
    }


class GetTop5PipelineResponse(pydantic.BaseModel):
    id: uuid.UUID
    name: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    script: Optional[str]
    subtitle_color: Optional[str]
    subtitle_highlight_color: Optional[str]
    volume_adjustment: Optional[str]
    logs: Optional[str]


@router.get('/{pipeline_id}', response_model=GetTop5PipelineResponse)
async def get_top5_pipeline(pipeline_id: uuid.UUID, db: orm.Session = fastapi.Depends(database.get_db)):
    record = crud.get_pipeline_record(db, pipeline_id)
    if record is None:
        raise HTTPException(status_code=404, detail='Pipeline not found')

    return {
        'id': record.id,
        'name': record.name,
        'status': record.status,
        'created_at': record.created_at,
        'updated_at': record.updated_at,
        'script': record.script,
        'subtitle_color': record.subtitle_color,
        'subtitle_highlight_color': record.subtitle_highlight_color,
        'volume_adjustment': record.volume_adjustment,
        'logs': record.logs,
    }


class ListTop5PipelineResponse(pydantic.BaseModel):
    id: uuid.UUID
    name: Optional[str]
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@router.get('/', response_model=list[ListTop5PipelineResponse])
async def list_top5_pipelines(db: orm.Session = fastapi.Depends(database.get_db)):
    records = crud.get_top5_pipeline_records(db)
    return [
        {
            'id': record.id,
            'name': record.name,
            'status': record.status,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
        }
        for record in records
    ]


def file_type_to_folder(file_type: str) -> str:
    if file_type == 'video':
        return 'videos'
    elif file_type == 'photo':
        return 'photos'
    elif file_type == 'sound_effect':
        return 'sound_effects'
    elif file_type == 'video_effect':
        return 'video_effects'
    elif file_type == 'music':
        return 'music'
    else:
        raise ValueError('Invalid file type')


@router.post('/{pipeline_id}/upload')
async def upload_top5_pipeline_file(
        pipeline_id: uuid.UUID,
        file: fastapi.UploadFile = fastapi.File(...),
        db: orm.Session = fastapi.Depends(database.get_db),
        file_type: str = fastapi.Form(...),
):
    try:
        pipeline_record = crud.get_pipeline_record(db, pipeline_id)
        if pipeline_record is None:
            raise HTTPException(status_code=404, detail='Pipeline not found')

        folder = file_type_to_folder(file_type)
        file_path = os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder, file.filename)
        with open(file_path, 'wb') as f:
            f.write(await file.read())
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{pipeline_id}/files')
async def list_top5_pipeline_files(pipeline_id: uuid.UUID):
    try:
        files = {
            'input': {},
            'output': None
        }

        for folder in os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input')):
            if os.path.isdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder)):
                files['input'][folder] = os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder))

        for file in os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'output')):
            files['output'] = file
        return files
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{pipeline_id}/file')
async def download_top5_pipeline_file(
        pipeline_id: uuid.UUID,
        file_path: str = fastapi.Query(...),
):
    try:
        if not file_path.startswith('input') and not file_path.startswith('output'):
            raise HTTPException(status_code=400, detail='Invalid file path')

        file_path = os.path.join(MEDIA_PATH, str(pipeline_id), file_path)
        return responses.FileResponse(file_path)
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


class RunTop5PipelineRequest(pydantic.BaseModel):
    background_video: str
    background_music: str
    video_effect: str

    places_videos: list[str]

    script: str
    subtitle_color: str = 'white'
    subtitle_highlight_color: str = '#7710e2'
    volume_adjustment: int = -25


pipeline_log_queues: dict[str, queue.Queue] = {}


class QueueHandler(logging.Handler):
    def __init__(self, queue: queue.Queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        print(record.msg)
        self.queue.put(record)


def run_pipeline_thread(db: orm.Session, record: crud.TOP5PipelineRecord, structure: pipeline.TOP5PipelineConfig,
                        elevenlabs_api_key: str):
    logger = logging.getLogger(str(record.id))
    logger.setLevel(logging.INFO)

    q = queue.Queue()
    queue_handler = QueueHandler(q)
    logger.addHandler(queue_handler)

    pipeline_log_queues[str(record.id)] = q

    try:
        p = pipeline.TOP5Pipeline(
            logger=logger,
            config=structure,
            elevenlaps_api_key=elevenlabs_api_key,
            working_dir=os.path.join(MEDIA_PATH, str(record.id)),
        )

        p.run(
            script=record.script,
            subtitle_color=record.subtitle_color,
            subtitle_highlight_color=record.subtitle_highlight_color,
            background_music_volume_adjustment=record.volume_adjustment,
        )

    except Exception as e:
        logging.error(str(e))
        crud.update_pipeline_record_status(db, record.id, 'failed')

        # Remove the logger from the dictionary
        del pipeline_log_queues[str(record.id)]
        return

    # Remove the logger from the dictionary
    del pipeline_log_queues[str(record.id)]
    crud.update_pipeline_record_status(db, record.id, 'completed')


@router.post('/{pipeline_id}/run')
async def run_top5_pipeline(
        pipeline_id: uuid.UUID,
        structure: RunTop5PipelineRequest,
        db: orm.Session = fastapi.Depends(database.get_db)):
    try:
        pipeline_record = crud.get_pipeline_record(db, pipeline_id)
        if pipeline_record is None:
            raise HTTPException(status_code=404, detail='Pipeline not found')

        elevenlabs_api_key = secrets_crud.get_secret(db, 'elevenlabs_api_key')
        if elevenlabs_api_key is None:
            raise HTTPException(status_code=500, detail='Elevenlabs API key is not configured')

        pipeline_record = crud.update_pipeline_record(
            db,
            pipeline_record.id,
            script=structure.script,
            volume_adjustment=structure.volume_adjustment,
            subtitle_color=structure.subtitle_color,
            subtitle_highlight_color=structure.subtitle_highlight_color,
        )

        structure = pipeline.TOP5PipelineConfig(
            background_video=structure.background_video,
            background_music=structure.background_music,
            video_effect=structure.video_effect,
            places_videos=structure.places_videos,
        )

        threading.Thread(target=run_pipeline_thread, args=(db, pipeline_record, structure)).start()

        crud.update_pipeline_record_status(db, pipeline_record.id, 'started')

    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))

    return {
        'status': pipeline_record.status
    }
