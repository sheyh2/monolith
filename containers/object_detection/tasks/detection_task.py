import numpy as np

from ship.core.base_task import BaseTask
from ship.setting import absolute_path


class ObjectDetectionTask(BaseTask):
    """Task for object detection using RTDETR"""

    def run(self, frame: np.ndarray) -> dict:
        """Detect objects in frame"""
        from ultralytics import RTDETR

        model = RTDETR(absolute_path('weights/rtdetr-x.pt'))

        if not model:
            return {'boxes': [], 'confidences': [], 'class_ids': []}

        detections = model.predict(frame, conf=0.5, verbose=False)

        if not detections or len(detections) == 0:
            return {'boxes': [], 'confidences': [], 'class_ids': []}

        if isinstance(detections, list):
            detections = detections[0]

        boxes = detections.boxes
        bbox = boxes.xywh.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        class_id = boxes.cls.cpu().numpy().astype(int)

        return {
            'boxes': bbox,
            'confidences': conf,
            'class_ids': class_id
        }