import logging
import os
import threading
import uuid

import fastapi
import fastapi.responses as responses
import queue
import pydantic

import sqlalchemy.orm as orm

import app.domains.pipelines.top5.crud as crud
import app.database.database as database
from app.config import MEDIA_PATH

import services.pipelines.top5_generator.pipeline as pipeline

pipeline_log_queues: dict[str, queue.Queue] = {}


class QueueHandler(logging.Handler):
    def __init__(self, queue: queue.Queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        print(record.msg)
        self.queue.put(record)


router = fastapi.APIRouter()


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class InitRequest(pydantic.BaseModel):
    script: str
    volume_adjustment: int
    subtitle_color: str
    subtitle_highlight_color: str


class InitResponse(pydantic.BaseModel):
    id: uuid.UUID
    status: str


@router.post('/init', response_model=InitResponse)
async def init_pipeline(request: InitRequest, db: orm.Session = fastapi.Depends(get_db)):
    try:
        record = crud.create_pipeline_record(
            db,
            request.script,
            request.volume_adjustment,
            request.subtitle_color,
            request.subtitle_highlight_color
        )

        os.makedirs(os.path.join(MEDIA_PATH, str(record.id)))
        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'input'))
        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'input', 'videos'))
        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'input', 'photos'))
        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'input', 'sound_effects'))

        os.makedirs(os.path.join(MEDIA_PATH, str(record.id), 'output'))
    except Exception as e:
        logging.error(str(e))
        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })

    return {
        'id': record.id,
        'status': record.status
    }


def file_type_to_folder(file_type: str) -> str:
    if file_type == 'video':
        return 'videos'
    elif file_type == 'photo':
        return 'photos'
    elif file_type == 'sound_effect':
        return 'sound_effects'
    else:
        raise ValueError('Invalid file type')


@router.post('/{pipeline_id}/upload')
async def upload_file(
        pipeline_id: uuid.UUID,
        file: fastapi.UploadFile = fastapi.File(...),
        db: orm.Session = fastapi.Depends(get_db),
        file_type: str = fastapi.Form(...),
):
    try:
        pipeline_record = crud.get_pipeline_record(db, pipeline_id)
        if pipeline_record is None:
            return fastapi.Response(status_code=404, content={
                'error': 'Pipeline not found'
            })

        folder = file_type_to_folder(file_type)
        file_path = os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder, file.filename)
        with open(file_path, 'wb') as f:
            f.write(await file.read())
    except Exception as e:
        logging.error(str(e))
        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })


@router.get('/{pipeline_id}/files')
async def list_files(pipeline_id: uuid.UUID):
    try:
        files = {
            'input': {},
            'output': None
        }

        for folder in os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input')):
            # check if folder is a directory
            if not os.path.isdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder)):
                continue

            files['input'][folder] = os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'input', folder))

        for file in os.listdir(os.path.join(MEDIA_PATH, str(pipeline_id), 'output')):
            files['output'] = file
        return files
    except Exception as e:
        logging.error(str(e))
        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })


@router.get('/{pipeline_id}/file')
async def download_file(
        pipeline_id: uuid.UUID,
        file_path: str = fastapi.Query(...),
):
    try:
        if not file_path.startswith('input') and not file_path.startswith('output'):
            raise ValueError('Invalid file path')

        file_path = os.path.join(MEDIA_PATH, str(pipeline_id), file_path)
        return responses.FileResponse(file_path)
    except Exception as e:
        logging.error(str(e))
        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })


@router.get('/{pipeline_id}/status')
async def get_pipeline_status(pipeline_id: uuid.UUID, db: orm.Session = fastapi.Depends(get_db)):
    record = crud.get_pipeline_record(db, pipeline_id)
    if record is None:
        return fastapi.Response(status_code=404, content={
            'error': 'Pipeline not found'
        })

    return {
        'status': record.status
    }


def run_pipeline_thread(db: orm.Session, record: crud.TOP5PipelineRecord):
    logger = logging.getLogger(str(record.id))
    logger.setLevel(logging.INFO)

    q = queue.Queue()
    queue_handler = QueueHandler(q)
    logger.addHandler(queue_handler)

    pipeline_log_queues[str(record.id)] = q

    try:
        p = pipeline.TOP5Pipeline(

        )

        p.run(
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


@router.get('/{pipeline_id}/run')
async def run_pipeline(pipeline_id: uuid.UUID, db: orm.Session = fastapi.Depends(get_db)):
    record = crud.get_pipeline_record(db, pipeline_id)
    if record is None:
        return fastapi.Response(status_code=404, content={
            'error': 'Pipeline not found'
        })
    try:
        threading.Thread(target=run_pipeline_thread, args=(db, record)).start()

        crud.update_pipeline_record_status(db, record.id, 'started')

    except Exception as e:
        logging.error(str(e))
        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })

    return {
        'status': record.status
    }
