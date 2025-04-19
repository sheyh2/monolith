import cv2
import numpy as np
from rfdetr import RFDETRBase
import supervision as sv
from tracking.strong_sort.strong_sort import StrongSORT
from ultralytics import RTDETR
from logging import warning as log_warning


class ObjectTracking:
    def __init__(self, draw=False, device='cuda:0', detection_model_type='rtdetr'):
        self.draw = draw
        self.device = device
        self.bbox_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()

        self.model = RFDETRBase() if detection_model_type == 'rfdetr' else RTDETR('rtdetr-x.pt')
        self.tracker = StrongSORT(
            model_weights='tracking/weights/osnet_ain_x1_0_msmt17.pt',
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

    def _xyxy_to_xywh(self, xyxy):
        x1, y1, x2, y2 = xyxy
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = x2 - x1, y2 - y1
        return np.array([cx, cy, w, h])

    def draw_annotated_frame(self, frame, tracks):
        if tracks is None:
            return frame

        for track in tracks:
            try:
                x, y, x1, y1, obj_id, _, _ = map(int, track[:7])
                cv2.rectangle(frame, (x, y), (x1, y1), (0, 255, 0), 2)
                cv2.putText(frame, f'ID: {obj_id}', (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            except Exception as e:
                log_warning(f"Annotation error: {e}")
        return frame

    def call(self, frame):
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            log_warning("Frame is empty or invalid")
            return None

        try:
            detections = self.model.predict(frame, conf=0.6, classes=[0], verbose=False)
            if not detections:
                log_warning("No detections found")
                return None
            
            if isinstance(detections, list):
                detections = detections[0]

            if hasattr(detections, 'boxes'):
                boxes = detections.boxes
                xyxy = boxes.xywh.cpu().numpy()
                conf = boxes.conf.cpu().numpy()
                class_id = boxes.cls.cpu().numpy()
            elif isinstance(detections, sv.Detections):
                xyxy = detections.xyxy
                conf = detections.confidence
                class_id = detections.class_id
            else:
                log_warning(f"Unsupported detection format: {type(detections)}")
                return None

            if len(xyxy) == 0:
                log_warning("No valid detections found")
                return None
            # print(xywh, conf, class_id)
            # xyxy = self._xyxy_to_xywh(xyxy)
            temp = self.tracker.update(xyxy, conf, class_id, frame)
            # print(temp)
            return temp

        except Exception as e:
            log_warning(f"Detection/tracking error: {e}")
            return None


    def run(self, video_path='StrongSORT_OSNet/test.mp4'):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            log_warning("Video could not be opened.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            tracks = self.call(frame)
            # if self.draw:
            # print(tracks)
            frame = self.draw_annotated_frame(frame, tracks)

            cv2.imshow('Tracking and ReID', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    tracker = ObjectTracking(draw=True, detection_model_type='rfdetr')
    tracker.run()
