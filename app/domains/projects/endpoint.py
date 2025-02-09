import datetime
import os
import typing
import uuid
from typing import Optional

import fastapi
import fastapi.responses as responses
import pydantic
import sqlalchemy.orm as orm

from app.config import PROJECTS_PATH
from app.database import database
import app.domains.projects.crud as crud
from app.auth import get_current_user

router = fastapi.APIRouter()


class CreateNewProjectRequest(pydantic.BaseModel):
    name: str


class CreateNewProjectResponse(pydantic.BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@router.post('/', response_model=CreateNewProjectResponse, tags=['Projects'])
async def create_new_project(request: CreateNewProjectRequest, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    record = crud.create_project(db, user['sub'], request.name)

    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id)))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input'))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input', 'videos'))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input', 'photos'))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input', 'music'))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input', 'video_effects'))
    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'input', 'sound_effects'))

    os.makedirs(os.path.join(PROJECTS_PATH, str(record.id), 'output'))

    return {
        'id': record.id,
        'name': record.name,
        'created_at': record.created_at,
        'updated_at': record.updated_at,
    }


class GetProjectResponse(pydantic.BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@router.get('/{project_id}', response_model=GetProjectResponse, tags=['Projects'])
async def get_project(project_id: uuid.UUID, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    project = crud.get_project_by_id(db, user['sub'], project_id)

    return {
        'id': project.id,
        'name': project.name,
        'created_at': project.created_at,
        'updated_at': project.updated_at,
    }


@router.get('/', response_model=list[GetProjectResponse], tags=['Projects'])
async def get_projects(db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    projects = crud.get_projects(db, user['sub'])

    return [
        {
            'id': project.id,
            'name': project.name,
            'created_at': project.created_at,
            'updated_at': project.updated_at,
        }
        for project in projects
    ]


class GetProjectTasksResponse(pydantic.BaseModel):
    id: uuid.UUID
    tool_name: str

    status: str
    error_message: Optional[str]

    json_params: Optional[str]

    created_at: datetime.datetime
    updated_at: datetime.datetime


@router.get('/{project_id}/tasks', response_model=list[GetProjectTasksResponse], tags=['Projects'])
def get_project_tasks(project_id: uuid.UUID, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)):
    tasks = crud.get_tasks_by_project_id(db, user['sub'], project_id)

    return [{
        'id': record.id,
        'tool_name': record.tool_name,
        'status': record.status,
        'error_message': record.error_message,
        'json_params': record.json_params,
        'created_at': record.created_at,
        'updated_at': record.updated_at,
    }
        for record in tasks
    ]


@router.get('/{project_id}/files', tags=['Projects'])
def list_project_files(project_id: uuid.UUID, user: dict = fastapi.Depends(get_current_user)):  
    files = list_files(os.path.join(PROJECTS_PATH, str(project_id)))

    return files


@router.post('/{project_id}/files/upload', tags=['Projects'])
async def upload_project_file(
        project_id: uuid.UUID,
        file: fastapi.UploadFile = fastapi.File(...),
        file_type: str = fastapi.Form(...),
        user: dict = fastapi.Depends(get_current_user)
):
    folder = file_type_to_folder(file_type)
    file_path = os.path.join(PROJECTS_PATH, str(project_id), 'input', folder, file.filename)
    with open(file_path, 'wb') as f:
        f.write(await file.read())


@router.get('/{project_id}/files/download', tags=['Projects'])
def download_file(
        project_id: uuid.UUID,
        file_path: str,
        user: dict = fastapi.Depends(get_current_user)
):
    file_path = os.path.join(PROJECTS_PATH, str(project_id), file_path)
    return responses.FileResponse(path=file_path)

@router.delete('/{project_id}/files/delete', tags=['Projects'])
def delete_file(
        project_id: uuid.UUID,
        file_path: str,
        user: dict = fastapi.Depends(get_current_user)
):
    file_path = os.path.join(PROJECTS_PATH, str(project_id), file_path)
    os.remove(file_path)


def list_files(directory):
    """Returns either a dict (if `directory` has subdirectories)
    or a list of files (if there are no subdirectories).
    Hidden files/folders (dotfiles) are skipped entirely."""
    subdirs = []
    files = []

    for entry in os.listdir(directory):
        # Skip hidden files/folders such as .DS_Store or any dotfile
        if entry.startswith('.'):
            continue

        full_path = os.path.join(directory, entry)

        if os.path.isdir(full_path):
            subdirs.append(entry)
        else:
            files.append(entry)

    # If there are subdirectories, return a dictionary
    if subdirs:
        result = {}
        for sd in subdirs:
            result[sd] = list_files(os.path.join(directory, sd))
        # NOTE: In a directory that has both subdirectories and files,
        #       this code *only* returns subdirectories. If you need
        #       to surface files too, you'd add them under a special key.
        return result
    else:
        # No subdirectories => just return the file list
        return files


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
