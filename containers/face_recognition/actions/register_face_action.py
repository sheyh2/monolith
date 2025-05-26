import numpy as np

from containers.face_recognition.models.face_data import PersonType
from ship.core.base_action import BaseAction


class RegisterFaceAction(BaseAction):
    """Action for registering new faces"""

    def run(self, image_data: np.ndarray, name: str, person_type: str = PersonType.CUSTOMER.value) -> tuple:
        """Register a new face"""
        import face_recognition

        try:
            # Detect faces
            face_locations = face_recognition.face_locations(image_data)

            if len(face_locations) == 0:
                return False, "No face detected"

            if len(face_locations) > 1:
                return False, "Multiple faces detected"

            # Extract encoding
            face_encoding = face_recognition.face_encodings(image_data, face_locations)[0]

            # Save to database
            face_repo = self.dependencies.get('face_repository')
            success = face_repo.register_person(name, face_encoding, person_type)

            if success:
                return True, f"Successfully registered {name} as {person_type}"
            else:
                return False, "Failed to save to database"

        except Exception as e:
            return False, f"Error registering face: {e}"