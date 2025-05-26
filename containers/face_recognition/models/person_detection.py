from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.enums import PersonType

Base = declarative_base()


class PersonDetection(Base):
    """Model for detected person IDs"""
    __tablename__ = "person_detections"

    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, nullable=False)
    track_id = Column(Integer, nullable=False)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    emotion = Column(String)
    face_top = Column(Integer)
    face_right = Column(Integer)
    face_bottom = Column(Integer)
    face_left = Column(Integer)
    body_top = Column(Integer)
    body_right = Column(Integer)
    body_bottom = Column(Integer)
    body_left = Column(Integer)
    person_type = Column(String, default=PersonType.CUSTOMER.value)
    timestamp = Column(DateTime, default=datetime.now)
