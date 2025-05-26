from containers.face_recognition.models.face_data import PersonType
from ship.core.base_task import BaseTask
import numpy as np


class FaceRecognitionTask(BaseTask):
    """Task for face recognition"""

    def run(self, frame: np.ndarray, face_location: tuple, known_faces: dict) -> tuple:
        """Recognize face in the given location"""
        import face_recognition

        try:
            # Extract face encoding
            face_encodings = face_recognition.face_encodings(frame, [face_location])

            if not face_encodings:
                return "unknown", PersonType.CUSTOMER.value

            face_encoding = face_encodings[0]

            # Check against known faces
            if len(known_faces['encodings']) > 0:
                matches = face_recognition.compare_faces(known_faces['encodings'], face_encoding)

                if True in matches:
                    matched_idx = matches.index(True)
                    name = known_faces['names'][matched_idx]
                    person_type = known_faces['person_type'][matched_idx]
                    return name, person_type

            return "unknown", PersonType.CUSTOMER.value

        except Exception as e:
            print(f"Error in face recognition: {e}")
            return "unknown", PersonType.CUSTOMER.value