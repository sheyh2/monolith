import numpy as np
from fastapi import Depends

from app.enums import CocoClass
from containers.face_recognition.models.face_data import PersonType, FaceLocation
from containers.face_recognition.models.person_detection import PersonDetection
from containers.face_recognition.repositories.face_repository import FaceRepository
from containers.face_recognition.repositories.person_detection_repository import PersonDetectionRepository
from containers.face_recognition.tasks.face_detector_task import FaceDetectorTask
from containers.object_detection.repositories.detection_repository import ObjectDetectionRepository
from ship.core.base_action import BaseAction
from containers.face_recognition.tasks.face_analysis_task import FaceAnalysisTask
from containers.face_recognition.tasks.face_recognition_task import FaceRecognitionTask
from containers.face_recognition.tasks.face_validation_task import FaceValidationTask
from containers.object_detection.tasks.detection_task import ObjectDetectionTask
from containers.tracking.tasks.tracking_task import TrackingTask


class ProcessFrameAction(BaseAction):
    """Main action for processing video frames"""

    def __init__(self):
        super().__init__()

        self.detection_task = ObjectDetectionTask(**self.dependencies)
        self.face_detector_task: FaceDetectorTask = Depends(FaceDetectorTask)

        self.person_detection_repo: PersonDetectionRepository = Depends(PersonDetectionRepository)
        self.object_detection_repo: ObjectDetectionRepository = Depends(ObjectDetectionRepository)
        self.face_repo: FaceRepository = Depends(FaceRepository)

    def run(self, frame: np.ndarray, frame_count: int) -> bool:
        """Process a single video frame"""
        try:

            # Task 1: Object Detection
            detections = self.detection_task.run(frame)

            # Save detections to database
            for i, box in enumerate(detections['boxes']):
                x1, y1, w1, h1 = box
                coco_class = CocoClass.from_value(detections['class_ids'][i])

                self.object_detection_repo.add(
                    frame_id=frame_count,
                    class_name=coco_class.name,
                    class_id=coco_class.value,
                    x1=x1, y1=y1, x2=x1 + w1, y2=y1 + h1,
                    confidence=round(detections['confidences'][i], 2)
                )

            # Task 2: Tracking
            tracking_task = TrackingTask(**self.dependencies)
            trackers = tracking_task.run(detections, frame)

            # Task 3: Face Processing
            faces, landmarks = self.face_detector_task.run(frame)

            for i, face in enumerate(faces):
                self._process_single_face(
                    frame,
                    face,
                    landmarks[i] if landmarks and i < len(landmarks) else None,
                    trackers,
                    frame_count
                )

            return True

        except Exception as e:
            print(f"Error processing frame: {e}")
            return False

    def _process_single_face(self, frame, face, landmark, trackers, frame_count):
        """Process a single detected face"""
        x_face, y_face, x1_face, y1_face = face[:4].astype(int)
        face_box = (x_face, y_face, x1_face, y1_face)

        # Find matching tracker
        matched_id, body_coordinates = self._match_face_to_tracker(face_box, trackers)

        if not matched_id:
            return

        # Validate face quality
        validation_task = FaceValidationTask()
        is_visible = False
        if landmark is not None:
            is_visible = validation_task.run(face[:4], landmark)

        # Get existing metadata
        person = self.person_detection_repo.get_face_metadata(matched_id)

        face_location = (y_face, x1_face, y1_face, x_face)  # top, right, bottom, left

        # Prepare face data
        face_data = {
            "face_location": face_location,
            "body_coordinates": body_coordinates
        }

        if person is not None:
            self._handle_existing_track(
                frame,
                person,
                matched_id,
                face_location,
                is_visible
            )
        else:
            self._handle_new_track(
                frame,
                face_data,
                matched_id,
                face_location,
                face_box,
                is_visible
            )

        # Save frame data
        tracking_repo = self.dependencies.get('tracking_repo')
        tracking_repo.save_frame_data(
            frame_count, matched_id, face_data, is_visible,
            face_data.get('person_type', PersonType.CUSTOMER.value)
        )

    def _match_face_to_tracker(self, face_box, trackers):
        """Match face detection to object tracker"""
        x_face, y_face, x1_face, y1_face = face_box

        for track in trackers:
            x, y, x1, y1, obj_id, _, _ = map(int, track[:7])
            if (
                    x <= x_face <= x1 and
                    y <= y_face <= y1 and
                    x <= x1_face <= x1 and
                    y <= y1_face <= y1
            ):
                body_coordinates = (y, x1, y1, x)
                return obj_id, body_coordinates

        return None, None

    def _handle_existing_track(self, frame, person: PersonDetection, matched_id, face_location, is_visible):
        """Handle processing for existing tracked face"""

        # Handle identification process
        if person.name == 'identifying..' and is_visible:
            recognition_task = FaceRecognitionTask(**self.dependencies)
            name, person_type = recognition_task.run(
                frame, face_location, self.face_repo.get_registered_persons()
            )

            if name != "unknown":
                self.face_repo.update_track_metadata(matched_id, {
                    "name": name,
                    "person_type": person_type
                })

    def _handle_new_track(self, frame, face_data, matched_id, face_location, face_box, is_visible):
        """Handle processing for new tracked face"""
        if not is_visible:
            face_data["name"] = "identifying..."
            face_data["person_type"] = PersonType.CUSTOMER.value
            return

        # Face Recognition
        recognition_task = FaceRecognitionTask(**self.dependencies)
        name, person_type = recognition_task.run(
            frame, face_location, self.face_repo.get_registered_persons()
        )

        face_data["name"] = name
        face_data["person_type"] = person_type

        # Face Analysis
        height, width = frame.shape[:2]
        x_face, y_face, x1_face, y1_face = face_box

        # Ensure coordinates are within bounds
        x_face = max(0, min(x_face, width))
        y_face = max(0, min(y_face, height))
        x1_face = max(0, min(x1_face, width))
        y1_face = max(0, min(y1_face, height))

        if x1_face > x_face and y1_face > y_face:
            face_img = frame[y_face:y1_face, x_face:x1_face]

            analysis_task = FaceAnalysisTask(**self.dependencies)
            analysis = analysis_task.run(face_img, matched_id)

            if analysis.age:
                face_data["age"] = analysis.age

            if analysis.gender:
                face_data["gender"] = analysis.gender

            if analysis.emotion:
                face_data["emotion"] = analysis.emotion

        # Save to database
        face_repo = self.dependencies.get('face_repository')
        detection = PersonDetection(
            track_id=matched_id,
            frame_id=self.dependencies.get('frame_count', 0),
            name=name,
            person_type=PersonType(person_type),
            face_location=FaceLocation(
                top=face_location[0], right=face_location[1],
                bottom=face_location[2], left=face_location[3]
            ),
            face_analysis=analysis if any([analysis.age, analysis.gender, analysis.emotion]) else None,
            is_visible=is_visible,
            body_coordinates=face_data.get('body_coordinates')
        )

        self.face_repo.save_face_detection(detection)
