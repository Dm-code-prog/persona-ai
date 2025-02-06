import logging
import os.path
import uuid
import threading

import fastapi
import pydantic
import sqlalchemy.orm as orm

from app.config import PROJECTS_PATH
import app.domains.projects.crud as projects_crud
from services.tools.video_unifier.video_unifier import VideoUnifier
from app.database import database

tool_name = 'unifier'

router = fastapi.APIRouter()


class Request(pydantic.BaseModel):
    video_name: str
    effect_name: str
    output_name: str

    blend_mode: str
    opacity: float


def run_unifier_thread(
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        request: Request,
        db: orm.Session,
):
    try:
        unifier = VideoUnifier(working_dir=os.path.join(PROJECTS_PATH, str(project_id)))

        unifier.unify(
            video_name=request.video_name,
            effect_name=request.effect_name,
            output_name=request.output_name,
            blend_mode=request.blend_mode,
            opacity=request.opacity
        )

        logging.info(f"video_unifier task {task_id} is complete")

        projects_crud.set_task_status(db, task_id, 'completed', None)
    except Exception as e:
        logging.error(f"video_unifier task {task_id} failed: {e}")
        
        projects_crud.set_task_status(db, task_id, 'failed', str(e))
    finally:
        db.close()


@router.put('/{project_id}/run', tags=['Tools'])
async def run_unifier(
        project_id: uuid.UUID,
        request: Request,
        db: orm.Session = fastapi.Depends(database.get_db)
):
    task = projects_crud.create_task(db, project_id, tool_name, request.model_dump_json())

    projects_crud.set_task_status(db, task.id, 'started', None)

    threading.Thread(
        target=run_unifier_thread,
        args=(project_id, task.id, request, db),
        daemon=True,
    ).start()

    return {
        'task_id': task.id,
        'status': 'started',
        'created_at': task.created_at,
        'updated_at': task.updated_at,
        'project_id': project_id,
        'tool_name': tool_name,
        'request': request.model_dump_json(),
    }
