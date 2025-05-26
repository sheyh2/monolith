from ship.core.base_task import BaseTask
from containers.face_recognition.models.face_data import FaceAnalysis
from PIL import Image
import numpy as np


class FaceAnalysisTask(BaseTask):
    """Task for analyzing face attributes (age, gender, emotion)"""

    def run(self, face_image: np.ndarray, track_id: int) -> FaceAnalysis:
        """Analyze face for age, gender, and emotion"""
        try:
            # Convert to PIL Image
            if face_image.size == 0 or face_image.shape[0] == 0 or face_image.shape[1] == 0:
                return FaceAnalysis()

            face_img = Image.fromarray(face_image)

            # Get estimators from dependencies
            age_estimator = self.dependencies.get('age_estimator')
            gender_estimator = self.dependencies.get('gender_estimator')
            emotion_estimator = self.dependencies.get('emotion_estimator')

            # Estimate attributes
            age = age_estimator(face_img) if age_estimator else None
            gender = gender_estimator(face_img) if gender_estimator else None
            emotion = emotion_estimator(face_img) if emotion_estimator else None

            return FaceAnalysis(age=age, gender=gender, emotion=emotion)

        except Exception as e:
            print(f"Error analyzing face for track {track_id}: {e}")
            return FaceAnalysis()