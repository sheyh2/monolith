from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
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


class ObjectDetection(Base):
    """Model for detected objects"""
    __tablename__ = "object_detections"

    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, nullable=False)
    class_ = Column(String, name="class", nullable=False)
    class_id = Column(Integer, nullable=False)
    x1 = Column(Integer)
    y1 = Column(Integer)
    x2 = Column(Integer)
    y2 = Column(Integer)
    conf = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)


class RegisteredPerson(Base):
    """Model for storing registered faces"""
    __tablename__ = "registered_persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    face_encoding = Column(LargeBinary, nullable=False)
    person_type = Column(String, default=PersonType.CUSTOMER.value)
    registered_date = Column(DateTime, default=datetime.now)


class PersonTrackingData(Base):
    """Model for face data for each frame"""
    __tablename__ = "person_tracking_data"

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
    is_frontal = Column(Boolean)
    person_type = Column(String, default=PersonType.CUSTOMER.value)
    timestamp = Column(DateTime, default=datetime.now)


class VideoFrame(Base):
    """Model for tracking frames"""
    __tablename__ = "video_frames"

    id = Column(Integer, primary_key=True, index=True)
    frame_path = Column(String, nullable=False)
    processed = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)