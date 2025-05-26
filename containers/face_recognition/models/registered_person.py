from sqlalchemy import Column, Integer, String, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.enums import PersonType

Base = declarative_base()

class RegisteredPerson(Base):
    """Model for storing registered faces"""
    __tablename__ = "registered_persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    face_encoding = Column(LargeBinary, nullable=False)
    person_type = Column(String, default=PersonType.CUSTOMER.value)
    registered_date = Column(DateTime, default=datetime.now)
