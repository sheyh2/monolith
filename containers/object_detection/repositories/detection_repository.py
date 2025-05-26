from containers.object_detection.models.object_detection import ObjectDetection
from ship.core.base_repository import BaseRepository
from datetime import datetime


class ObjectDetectionRepository(BaseRepository):
    """Repository for object detection operations"""

    def add(self, frame_id: int, class_name: str, class_id: int,
                       x1: float, y1: float, x2: float, y2: float,
                       confidence: float, timestamp=None) -> ObjectDetection:
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

        obj_detection = ObjectDetection()

        obj_detection.frame_id = frame_id
        obj_detection.class_ = class_name  # Note the underscore to match SQLAlchemy model
        obj_detection.class_id = class_id
        obj_detection.x1 = x1
        obj_detection.y1 = y1
        obj_detection.x2 = x2
        obj_detection.y2 = y2
        obj_detection.conf = confidence
        obj_detection.timestamp = timestamp

        try:
            self.db.add(obj_detection)
            self.db.commit()
            self.db.refresh(obj_detection)
            return obj_detection

        except Exception as e:
            self.db.rollback()
            raise e
