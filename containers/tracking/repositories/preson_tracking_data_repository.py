from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, List, Any

from containers.face_recognition.models.face_data import PersonType
from containers.tracking.models.person_tracking_data import PersonTrackingData


class PersonTrackingDataRepository:
    """Repository for working with PersonTrackingData model"""

    def __init__(self, db: Session):
        self.db = db

    def save_frame_data(self, frame_id: int, track_id: int, face_data: Dict[str, Any],
                        visible: bool, person_type: str = PersonType.CUSTOMER.value) -> PersonTrackingData:
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
            tracking_data = PersonTrackingData(
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

    def get_by_frame_id(self, frame_id: int) -> List[PersonTrackingData]:
        """Get all person tracking data for a specific frame"""
        return self.db.query(PersonTrackingData).filter_by(frame_id=frame_id).all()
