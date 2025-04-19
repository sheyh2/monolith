from pathlib import Path
from time import time
import cv2
import numpy as np
import supervision as sv
import torch
from ultralytics import RTDETR

from bytetrack.byte_tracker import BYTETracker
# from strong_sort.strong_sort import StrongSORT
from util import YamlParser

SAVE_VIDEO = False
# 'bytetrack' or 'strongsort'
TRACKER = 'bytetrack'


class ObjectDetection:
    """
    Class for object detection, tracking, and visualization.
    """
    def __init__(self, capture_index):
       
        self.capture_index = capture_index
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print("Using Device: ", self.device)
        
        self.model = RTDETR("weights/rtdetr-x.pt")
        if self.model is None:
            raise ValueError("Model could not be loaded. Please check the model path and weights.")

        self.CLASS_NAMES_DICT = self.model.names
        
        # print(self.CLASS_NAMES_DICT)
    
        self.box_annotator = sv.BoxAnnotator(sv.Color.BLUE, thickness=2)
    
        self.tracker_config = 'bytetrack/config/bytetrack.yaml'
        cfg = YamlParser()
        cfg.merge_from_file(self.tracker_config)

        self.tracker = BYTETracker(
            args = cfg,
        )

    
    def plot_bboxes(self, results, frame):
        """
        Annotates a given frame with bounding boxes and labels based on detection results.

        Args:
            results: The detection results containing bounding boxes, class ids, and confidence scores.
            frame: The frame/image to be annotated.

        Returns:
            The annotated frame with bounding boxes and labels.
        """
        boxes = results[0].boxes.cpu().numpy()
        class_id = boxes.cls
        conf = boxes.conf
        xyxy = boxes.xyxy
        
    
        class_id = class_id.astype(np.int32)
    
        
        # Setup detections for visualization
        detections = sv.Detections(
                    xyxy=xyxy,
                    confidence=conf,
                    class_id=class_id,
                    )
        # print(detections)
        # Format custom labels
        # self.labels = [f"{self.CLASS_NAMES_DICT[class_id]}" for xyxy, mask, confidence, class_id, track_id, data in detections]
    
        
        # Annotate and display frame
        frame = self.box_annotator.annotate(scene=frame, detections=detections)
        
        return frame
    
    
    
    def __call__(self):

        cap = cv2.VideoCapture(self.capture_index)
        assert cap.isOpened(), 'Cannot capture source'  
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if SAVE_VIDEO:
            out = cv2.VideoWriter('output.mp4', cv2.VideoWriter_fourcc(*'mp4'), 25, 8, (1280, 720))


        # if hasattr(tracker, 'model'):
        #     if hasattr(tracker.model, 'wormup'):
        #         tracker.model.warmup()

        curr_frames, perv_frame = None, None

        while True:
            start_time = time()
            ret, frame = cap.read()
            assert ret, 'Frame read error'

            # if hasattr(tracker, 'track') and hasattr(tracker.tracker, 'camera_update'):
            #     if perv_frame is not None and curr_frames is not None:
            #         tracker.tracker.camera_update(curr_frames, perv_frame)

            results = self.model.predict(frame, classes=[0], conf=0.7, verbose=False)
            # frame = self.plot_bboxes(results, frame)

            boxes = results[0].boxes.cpu()
            class_id = boxes.cls
            conf = boxes.conf
            xyxy = boxes.xyxy
        
            trackers = self.tracker.update(bboxes=xyxy, scores=conf, img_info=frame.shape, img_size=frame.shape)
            for track in trackers:
                bbox = track.tlbr
                x, y, x1, y1 = map(int, bbox)
                tracked_id = track.track_id
                top_left = (x, y - 10)
                cv2.putText(frame, f"ID: {tracked_id}", top_left, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.rectangle(frame, (x, y), (x1, y1), (255, 0, 0), 2)

            if SAVE_VIDEO:
                out.write(frame)

            end_time = time()
            fps = 1/np.round(end_time - start_time, 2)
             
            cv2.putText(frame, f'FPS: {int(fps)}', (20,70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 2)

            cv2.imshow('Detection and Tracking', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()

detector = ObjectDetection(capture_index='test.mp4')
detector()
