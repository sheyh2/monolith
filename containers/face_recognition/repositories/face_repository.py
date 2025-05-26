from containers.face_recognition.models.registered_person import RegisteredPerson
from ship.core.base_repository import BaseRepository
from typing import List, Dict
import numpy as np


class FaceRepository(BaseRepository):
    """Repository for face-related database operations"""

    def get_registered_persons(self) -> Dict[str, List]:
        """Get all registered persons from database"""
        # Implementation would interact with actual database

        known_faces = {'encodings': [], 'names': [], 'person_type': []}

        try:
            registered_persons = self.db.query(RegisteredPerson).all()

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

    def register_person(self, name: str, encoding: np.ndarray, person_type: str) -> RegisteredPerson:
        """Register a known face in the database"""
        try:
            # Convert numpy array to binary for storage
            face_encoding_binary = encoding.tobytes()

            registered_person = RegisteredPerson(
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

    def update_track_metadata(self, track_id: int, metadata: Dict) -> bool:
        """Update track metadata"""
        self.db.query(RegisteredPerson).filter_by(track_id=track_id).update(metadata)
        self.db.commit()

        return True
