import asyncio
import logging
import os
import threading
import uuid

import fastapi
import pydantic
import sqlalchemy.orm as orm

import app.database.database as database
from app.config import PROJECTS_PATH
from services.tools.pause_cutter.pause_cutter import PauseCutter

import app.domains.projects.crud as projects_crud

tool_name = 'pause_cutter'

router = fastapi.APIRouter()


class RunRequest(pydantic.BaseModel):
    pause_threshold: float = 0.5
    pause_padding: float = 0.1
    whisper_model: str = 'small'

    video_name: str
    output_name: str


def run_pause_cutter_tool_thread(
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        request: RunRequest,
        db: orm.Session
):
    try:
        pause_cutter = PauseCutter(
            working_dir=os.path.join(PROJECTS_PATH, str(project_id)),
            whisper_model=request.whisper_model,
        )

        pause_cutter.run(
            video_name=request.video_name,
            output_name=request.output_name,
            pause_threshold=request.pause_threshold,
            pad=request.pause_padding
        )

        logging.info("pause cutter tool completed")
        projects_crud.set_task_status(db, task_id, 'completed', None)
    except Exception as e:
        projects_crud.set_task_status(db, task_id, 'failed', str(e))

        logging.info(f"failed to run pause cutter tool: {str(e)}")
    finally:
        db.close()


@router.put('/{project_id}/run', tags=['Tools'])
async def run_pause_cutter_tool(
        project_id: uuid.UUID,
        request: RunRequest,
        db: orm.Session = fastapi.Depends(database.get_db)):
    task = projects_crud.create_task(db, project_id, tool_name, request.model_dump_json())

    projects_crud.set_task_status(db, task.id, 'started', None)

    # run the task in a seperate thread and return the task id to the user immediately

    threading.Thread(
        target=run_pause_cutter_tool_thread,
        args=(project_id, task.id, request, db),
        daemon=True,
    ).start()


    return {
        'id': task.id,
        'status': task.status,
        'created_at': task.created_at,
        'updated_at': task.updated_at,
    }
