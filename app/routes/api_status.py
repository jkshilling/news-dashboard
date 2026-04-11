from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import status_service

router = APIRouter(prefix="/api")


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    return status_service.get_status_table(db)
