from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any, Type
from app import models
from app.enums import PersonType
from app.models import PersonDetection, ObjectDetection


class PersonDetectionRepository:
    """Repository for working with PersonDetection model"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int) -> Optional[models.PersonDetection]:
        """Get a person detection by ID"""
        return self.db.query(models.PersonDetection).filter(models.PersonDetection.id == id).first()

    def get_by_track_id(self, track_id: int) -> list[Type[PersonDetection]]:
        """Get all person detections by track ID"""
        return self.db.query(models.PersonDetection).filter_by(track_id=track_id).all()

    def save_face_data(self, frame_id: int, track_id: int, face_data: Dict[str, Any]) -> models.PersonDetection:
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
            person_detection = models.PersonDetection(
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
            persons = self.db.query(models.PersonDetection).filter(models.PersonDetection.track_id == track_id).all()
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

    def get_face_data(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Get stored data for a specific track_id"""
        person = (
            self.db.query(models.PersonDetection)
            .filter(models.PersonDetection.track_id == track_id)
            .first()
        )

        if person:
            return {
                "name": person.name,
                "age": person.age,
                "gender": person.gender,
                "emotion": person.emotion,
                "person_type": person.person_type,
                "face_location": (person.face_top, person.face_right, person.face_bottom, person.face_left),
                "body_top": person.body_top,
                "body_right": person.body_right,
                "body_bottom": person.body_bottom,
                "body_left": person.body_left
            }
        return None


class ObjectDetectionRepository:
    """Repository for working with ObjectDetection model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, frame_id: int, class_name: str, class_id: int,
               x1: Optional[int] = None, y1: Optional[int] = None,
               x2: Optional[int] = None, y2: Optional[int] = None,
               confidence: Optional[float] = None, timestamp: Optional[datetime] = None) -> models.ObjectDetection:
        """Create a new object detection record"""
        # Convert numpy types to Python types if needed
        if frame_id is not None:
            frame_id = int(frame_id)
        if class_id is not None:
            class_id = int(class_id)
        if x1 is not None:
            x1 = int(x1)
        if y1 is not None:
            y1 = int(y1)
        if x2 is not None:
            x2 = int(x2)
        if y2 is not None:
            y2 = int(y2)
        if confidence is not None:
            confidence = float(confidence)

        # Use current timestamp if none provided
        if timestamp is None:
            timestamp = datetime.now()

        try:
            obj_detection = models.ObjectDetection(
                frame_id=frame_id,
                class_=class_name,  # Note the underscore to match SQLAlchemy model
                class_id=class_id,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                conf=confidence,
                timestamp=timestamp
            )

            self.db.add(obj_detection)
            self.db.commit()
            self.db.refresh(obj_detection)
            return obj_detection

        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_frame_id(self, frame_id: int) -> list[Type[ObjectDetection]]:
        """Get all object detections for a specific frame"""
        return self.db.query(models.ObjectDetection).filter_by(frame_id=frame_id).all()


class RegisteredPersonRepository:
    """Repository for working with RegisteredPerson model"""

    def __init__(self, db: Session):
        self.db = db

    def register_person(self, name: str, face_encoding: np.ndarray,
                        person_type: str = PersonType.CUSTOMER.value) -> models.RegisteredPerson:
        """Register a known face in the database"""
        try:
            # Convert numpy array to binary for storage
            face_encoding_binary = face_encoding.tobytes()

            registered_person = models.RegisteredPerson(
                name=name,
                face_encoding=face_encoding_binary,
                person_type=person_type
            )

            self.db.add(registered_person)
            self.db.commit()
            self.db.refresh(registered_person)
            return registered_person

        except Exception as e:
            self.db.rollback()
            raise e

    def get_all_persons(self) -> Dict[str, List]:
        """Retrieve all known faces from database"""
        known_faces = {'encodings': [], 'names': [], 'person_type': []}

        try:
            registered_persons = self.db.query(models.RegisteredPerson).all()

            for person in registered_persons:
                # Convert binary back to numpy array
                face_encoding = np.frombuffer(person.face_encoding, dtype=np.float64)
                known_faces['encodings'].append(face_encoding)
                known_faces['names'].append(person.name)
                known_faces['person_type'].append(person.person_type)

            return known_faces

        except Exception as e:
            print(f"Error retrieving known faces: {e}")
            raise e


class PersonTrackingDataRepository:
    """Repository for working with PersonTrackingData model"""

    def __init__(self, db: Session):
        self.db = db

    def save_frame_data(self, frame_id: int, track_id: int, face_data: Dict[str, Any],
                        visible: bool, person_type: str = PersonType.CUSTOMER.value) -> models.PersonTrackingData:
        """Save data for each frame to the person_tracking_data table"""
        name = face_data.get("name", "unknown")

        # Convert numpy.int64 to standard Python int if needed
        age = int(face_data.get("age")) if face_data.get("age") is not None else None
        gender = face_data.get("gender")
        emotion = face_data.get("emotion")

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
            tracking_data = models.PersonTrackingData(
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
                is_frontal=visible,
                person_type=person_type,
                timestamp=timestamp
            )

            self.db.add(tracking_data)
            self.db.commit()
            self.db.refresh(tracking_data)
            return tracking_data

        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_frame_id(self, frame_id: int) -> List[models.PersonTrackingData]:
        """Get all person tracking data for a specific frame"""
        return self.db.query(models.PersonTrackingData).filter_by(frame_id=frame_id).all()


class VideoFrameRepository:
    """Repository for working with VideoFrame model"""

    def __init__(self, db: Session):
        self.db = db

    def get_unprocessed_frames(self) -> List[Dict[str, Any]]:
        """Get all unprocessed video frames"""
        frames = self.db.query(models.VideoFrame).filter(models.VideoFrame.processed == False).all()

        if frames:
            return [
                {
                    "id": frame.id,
                    "frame_path": frame.frame_path,
                    "timestamp": frame.timestamp,
                }
                for frame in frames
            ]
        return []

    def mark_as_processed(self, frame_id: int) -> None:
        """Mark a frame as processed in the database"""
        try:
            frame = self.db.query(models.VideoFrame).filter(models.VideoFrame.id == frame_id).first()
            if frame:
                frame.processed = True
                self.db.commit()
            else:
                print(f"Frame with ID {frame_id} not found")
        except Exception as e:
            self.db.rollback()
            print(f"Error updating frame status: {e}")
            raise e

    def insert_frame(self, frame_path: str, timestamp: Optional[datetime] = None,
                     processed: bool = False) -> Optional[int]:
        """Insert a new frame record into the database"""
        if timestamp is None:
            timestamp = datetime.now()

        try:
            frame = models.VideoFrame(
                frame_path=frame_path,
                timestamp=timestamp,
                processed=processed
            )

            self.db.add(frame)
            self.db.commit()
            self.db.refresh(frame)
            return frame.id

        except Exception as e:
            self.db.rollback()
            print(f"Error inserting frame: {e}")
            return None


# Helper function to get all repositories
def get_repositories(db: Session):
    """Create and return all repositories"""
    return {
        "person_detection": PersonDetectionRepository(db),
        "object_detection": ObjectDetectionRepository(db),
        "registered_person": RegisteredPersonRepository(db),
        "person_tracking": PersonTrackingDataRepository(db),
        "video_frame": VideoFrameRepository(db)
    }