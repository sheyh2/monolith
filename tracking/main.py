from pathlib import Path
from time import time
import cv2
import numpy as np
import supervision as sv
import torch
from ultralytics import RTDETR

from tracking.bytetrack.byte_tracker import BYTETracker
# from strong_sort.strong_sort import StrongSORT
from tracking.util import YamlParser



class ObjectTracking:
    """
    Class for object detection, tracking, and visualization.
    """

    def __init__(self):



        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print("Using Device: ", self.device)

        self.model = RTDETR("weights/rtdetr-x.pt")
        if self.model is None:
            raise ValueError("Model could not be loaded. Please check the model path and weights.")



        # print(self.CLASS_NAMES_DICT)


        self.tracker_config = 'tracking/bytetrack/config/bytetrack.yaml'
        cfg = YamlParser()
        cfg.merge_from_file(self.tracker_config)

        self.tracker = BYTETracker(
            args=cfg,
        )
    def __call__(self,frame):

        results = self.model.predict(frame, classes=[0], conf=0.6, verbose=False)

        boxes = results[0].boxes.cpu()
        conf = boxes.conf
        xyxy = boxes.xyxy
        trackers = self.tracker.update(bboxes=xyxy, scores=conf, img_info=frame.shape, img_size=frame.shape)
        return trackers
