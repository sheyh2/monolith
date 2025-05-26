import numpy as np
from fastapi import Depends

from containers.face_recognition.actions.process_frame_action import ProcessFrameAction
from containers.face_recognition.actions.register_face_action import RegisterFaceAction
from containers.face_recognition.models.face_data import PersonType
from containers.face_recognition.repositories.face_repository import FaceRepository
from containers.face_recognition.repositories.tracking_repository import TrackingRepository
from containers.object_detection.repositories.detection_repository import ObjectDetectionRepository


class FaceProcessorService:
    """Main service class orchestrating face processing"""

    def __init__(self, session, recognition_attempts=3, data_path=None):
        # Initialize dependencies
        self.session = session
        self.frame_count = 0
        self.recognition_attempts = recognition_attempts

        # Initialize repositories
        self.face_repo = Depends(FaceRepository)
        self.tracking_repo = Depends(TrackingRepository)
        self.detection_repo = Depends(ObjectDetectionRepository)

        # Initialize models and dependencies
        self._init_dependencies(data_path)

        # Load known faces
        self.known_faces = self.face_repo.get_registered_persons()

        if data_path:
            self._load_faces_from_directories(data_path)

    def _init_dependencies(self, data_path):
        """Initialize all model dependencies"""

        # Initialize models (these would be injected in real implementation)
        try:
            from face.age_resnet_50 import AgeEstimator
            from face.gender_detection import GenderEstimator
            from face.res_emote_net_emotion import EmotionEstimator
            from face.face_pointing import process_image

            self.age_estimator = AgeEstimator()
            self.gender_estimator = GenderEstimator()
            self.emotion_estimator = EmotionEstimator()
            self.face_processor = type('FaceProcessor', (), {
                'detect_faces': lambda self, frame: process_image(frame)
            })()

        except ImportError as e:
            print(f"Warning: Could not import face analysis models: {e}")
            self.age_estimator = None
            self.gender_estimator = None
            self.emotion_estimator = None

        # COCO class names
        self.coco_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            # ... (add all COCO class names)
        ]

    def process_frame(self, frame: np.ndarray) -> bool:
        """Process a single frame"""
        self.frame_count += 1

        # Prepare dependencies for action
        dependencies = {
            'face_repository': self.face_repo,
            'tracking_repository': self.tracking_repo,
            'detection_repository': self.detection_repo,
            'age_estimator': self.age_estimator,
            'gender_estimator': self.gender_estimator,
            'emotion_estimator': self.emotion_estimator,
            'face_processor': self.face_processor,
            'known_faces': self.known_faces,
            'coco_names': self.coco_names,
            'frame_count': self.frame_count
        }

        # Execute main processing action
        action = ProcessFrameAction(**dependencies)
        return action.run(frame, self.frame_count)

    def register_face(self, image_data: np.ndarray, name: str, person_type: str) -> tuple:
        """Register a new face"""
        dependencies = {
            'face_repository': self.face_repo
        }

        action = RegisterFaceAction(**dependencies)
        result, message = action.run(image_data, name, person_type)

        # Update local cache if successful
        if result:
            self.known_faces = self.face_repo.get_registered_persons()

        return result, message

    def _load_faces_from_directories(self, base_path):
        """Load known faces from structured directories"""
        import os
        import face_recognition

        person_types = {
            'celebrities': PersonType.CELEBRITY.value,
            'waiters': PersonType.WAITER.value,
            'customers': PersonType.CUSTOMER.value
        }

        for category, person_type in person_types.items():
            category_path = os.path.join(base_path, category)

            if not os.path.exists(category_path):
                continue

            for person_name in os.listdir(category_path):
                person_dir = os.path.join(category_path, person_name)

                if not os.path.isdir(person_dir):
                    continue

                for image_file in os.listdir(person_dir):
                    if not image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        continue

                    image_path = os.path.join(person_dir, image_file)
                    try:
                        image = face_recognition.load_image_file(image_path)
                        result, message = self.register_face(image, person_name, person_type)
                        print(f"{'✓' if result else '✗'} {image_file}: {message}")
                    except Exception as e:
                        print(f"✗ Error processing {image_path}: {e}")