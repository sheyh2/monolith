import numpy as np

from ship.core.base_task import BaseTask
from ship.setting import absolute_path


class TrackingTask(BaseTask):
    """Task for object tracking"""

    def run(self, detections: dict, frame: np.ndarray) -> list:
        """Update tracker with new detections"""
        import torch
        from tracking.strong_sort import StrongSORT

        # Initialize device
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Initialize tracker
        tracker = StrongSORT(
            model_weights=absolute_path('tracking/weights/osnet_ain_x1_0_msmt17.pt'),
            device=device,
            fp16=False,
            max_dist=0.2,
            max_iou_distance=0.7,
            max_age=70,
            n_init=3,
            nn_budget=100,
            mc_lambda=0.9,
            ema_alpha=0.9
        )

        if not tracker:
            return []

        bbox = detections['boxes']
        conf = detections['confidences']
        class_id = detections['class_ids']

        if len(bbox) == 0:
            return []

        return tracker.update(bbox, conf, class_id, frame)