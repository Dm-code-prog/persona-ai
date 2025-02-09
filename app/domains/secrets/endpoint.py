import logging

import fastapi
import sqlalchemy.orm as orm
from fastapi import HTTPException

import app.database.database as database
import app.domains.secrets.crud as crud
from app.auth import get_current_user
router = fastapi.APIRouter()


@router.put('/put', tags=['Secrets'])
def put_secret(key: str, value: str, db: orm.Session = fastapi.Depends(database.get_db), user: dict = fastapi.Depends(get_current_user)): 
    try:
        crud.set_secret(db,user['sub'], key, value)
    except Exception as e:
        logging.error("failed to put a secret", e)

        return fastapi.Response(status_code=500, content={
            'error': str(e)
        })


@router.get('/get-insecure', tags=['Secrets'])
def get_secret_insecure(
        key: str = fastapi.Query(...),
        db: orm.Session = fastapi.Depends(database.get_db),
        user: dict = fastapi.Depends(get_current_user)
):
    try:
        record = crud.get_secret(db, user['sub'], key)
        if record is None:
            raise HTTPException(status_code=404, detail="Secret not found")
        return {
            'key': key,
            'value': record.value,
        }
    except Exception as e:
        logging.error(f"failed to get a secret {key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
