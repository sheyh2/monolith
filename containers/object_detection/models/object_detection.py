from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from app.enums import PersonType

Base = declarative_base()


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
