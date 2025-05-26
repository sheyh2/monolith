import numpy as np
import math

from ship.core.base_task import BaseTask


class FaceValidationTask(BaseTask):
    """Task for validating if face is suitable for recognition"""

    def run(self, face_box: tuple, landmarks: np.ndarray) -> bool:
        """Check if face is frontal and suitable for recognition"""
        x_face, y_face, x1_face, y1_face = face_box
        face_width = x1_face - x_face
        face_height = y1_face - y_face
        scale = (face_width + face_height) / 2.0

        # Extract landmark points
        left_eye, right_eye = np.array(landmarks[0]), np.array(landmarks[1])
        nose = np.array(landmarks[2])
        mouth_left, mouth_right = np.array(landmarks[3]), np.array(landmarks[4])

        # Calculate distances and angles
        eye_distance = np.linalg.norm(left_eye - right_eye)
        middle_eye = (left_eye + right_eye) / 2.0
        middle_mouth = (mouth_left + mouth_right) / 2.0
        face_vertical = np.linalg.norm(middle_mouth - middle_eye)

        def angle_between(p1, p2):
            return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

        eye_angle = angle_between(left_eye, right_eye)
        mouth_angle = angle_between(mouth_left, mouth_right)

        # Calculate ratios
        eye_ratio = eye_distance / scale
        vertical_ratio = face_vertical / scale

        nose_to_eyes = np.linalg.norm(nose - middle_eye)
        nose_to_mouth = np.linalg.norm(nose - middle_mouth)
        nose_ratio = nose_to_eyes / nose_to_mouth

        # Validation checks
        if abs(eye_angle) > 20 or abs(mouth_angle) > 20:
            return False
        if not (0.25 < eye_ratio < 0.55):
            return False
        if not (0.35 < vertical_ratio < 0.75):
            return False
        if nose_ratio < 0.8:
            return False

        return True