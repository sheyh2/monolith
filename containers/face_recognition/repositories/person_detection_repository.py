from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Optional, Any, Type
from app import models
from app.enums import PersonType
from containers.face_recognition.models.person_detection import PersonDetection


class PersonDetectionRepository:
    """Repository for working with PersonDetection model"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int) -> Optional[PersonDetection]:
        """Get a person detection by ID"""
        return self.db.query(PersonDetection).filter(PersonDetection.id == id).first()

    def get_by_track_id(self, track_id: int) -> list[Type[PersonDetection]]:
        """Get all person detections by track ID"""
        return self.db.query(PersonDetection).filter_by(track_id=track_id).all()

    def save_face_data(self, frame_id: int, track_id: int, face_data: Dict[str, Any]) -> PersonDetection:
        """Save face data for a detected person"""
        # Extract and convert data
        name = face_data.get("name", "unknown")

        # Convert numpy.int64 to standard Python int if needed
        age = int(face_data.get("age")) if face_data.get("age") is not None else None
        gender = face_data.get("gender")
        emotion = face_data.get("emotion")
        person_type = face_data.get("person_type", PersonType.CUSTOMER.value)

        # Face location
        face_location = face_data.get("face_location", (None, None, None, None))
        if face_location and len(face_location) == 4:
            # Convert numpy.int64 to standard Python int if needed
            top = int(face_location[0]) if face_location[0] is not None else None
            right = int(face_location[1]) if face_location[1] is not None else None
            bottom = int(face_location[2]) if face_location[2] is not None else None
            left = int(face_location[3]) if face_location[3] is not None else None
        else:
            top, right, bottom, left = None, None, None, None

        # Body location - convert numpy.int64 to standard Python int if needed
        body_top = int(face_data.get("body_top")) if face_data.get("body_top") is not None else None
        body_right = int(face_data.get("body_right")) if face_data.get("body_right") is not None else None
        body_bottom = int(face_data.get("body_bottom")) if face_data.get("body_bottom") is not None else None
        body_left = int(face_data.get("body_left")) if face_data.get("body_left") is not None else None

        timestamp = datetime.now()

        # Convert frame_id and track_id to standard Python int if needed
        if frame_id is not None:
            frame_id = int(frame_id)
        if track_id is not None:
            track_id = int(track_id)

        try:
            person_detection = PersonDetection(
                frame_id=frame_id,
                track_id=track_id,
                name=name,
                age=age,
                gender=gender,
                emotion=emotion,
                face_top=top,
                face_right=right,
                face_bottom=bottom,
                face_left=left,
                body_top=body_top,
                body_right=body_right,
                body_bottom=body_bottom,
                body_left=body_left,
                person_type=person_type,
                timestamp=timestamp
            )

            self.db.add(person_detection)
            self.db.commit()
            self.db.refresh(person_detection)
            return person_detection

        except Exception as e:
            self.db.rollback()
            raise e

    def update_by_track_id(self, track_id: int, updates: Dict[str, Any]) -> None:
        """Update any fields for all detections with a given track_id"""
        if not updates:
            print("No updates provided.")
            return

        try:
            persons = self.db.query(PersonDetection).filter(models.PersonDetection.track_id == track_id).all()
            for person in persons:
                for key, value in updates.items():
                    if hasattr(person, key):
                        setattr(person, key, value)

            self.db.commit()
            print(f"Updated track_id {track_id} with fields: {list(updates.keys())}")
        except Exception as e:
            self.db.rollback()
            print(f"Error updating fields: {e}")
            raise e

    def get_face_metadata(self, track_id: int) -> PersonDetection | None:
        """Get stored data for a specific track_id"""
        return (
            self.db.query(PersonDetection)
            .filter(PersonDetection.track_id == track_id)
            .first()
        )
