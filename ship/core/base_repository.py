from abc import ABC
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db


class BaseRepository(ABC):
    """Base repository interface"""

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
