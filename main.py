import numpy as np

np.float = float
from PIL import Image
import os
import face_recognition
import torch
import cv2
import numpy as np
import math
from face.age_resnet_50 import AgeEstimator
from face.face_pointing import process_image
from face.gender_detection import GenderEstimator
from face.res_emote_net_emotion import EmotionEstimator
from db_manager import DatabaseManager
from ultralytics import RTDETR

# Initialize all models
age_estimator = AgeEstimator()
gender_estimator = GenderEstimator()
emotion_estimator = EmotionEstimator()

from logging import warning as log_warning
from tracking.strong_sort import StrongSORT

# Константы для типов людей
PERSON_TYPE_CUSTOMER = 'customer'
PERSON_TYPE_WAITER = 'waiter'
PERSON_TYPE_CELEBRITY = 'celebrity'

coco_names = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus', 6: 'train', 7: 'truck',
              8: 'boat', 9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
              14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant', 21: 'bear',
              22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase',
              29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat',
              35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle',
              40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple',
              48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut',
              55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet',
              62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave',
              69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase',
              76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'}


class FaceProcessor:
    """
    Enhanced class for face detection, tracking, recognition, and analysis
    """

    def __init__(self, db_manager, recognition_attempts=3, data_path=None):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print("Using Device:", self.device)
        self.tracker = StrongSORT(
            model_weights='tracking/weights/osnet_ain_x1_0_msmt17.pt',
            device=self.device,
            fp16=False,
            max_dist=0.2,
            max_iou_distance=0.7,
            max_age=70,
            n_init=3,
            nn_budget=100,
            mc_lambda=0.9,
            ema_alpha=0.9
        )
        self.db_manager = db_manager
        self.frame_count = 0
        self.recognition_attempts = recognition_attempts
        self.data_path = data_path
        self.model = RTDETR('weights/rtdetr-x.pt')
        self.track_metadata = {}

        # Load known faces from database
        self.known_faces = self.db_manager.get_known_faces()
        # self.get_data = self.db_manager.get_frame_data
        # self.update_by_track_id = self.db_manager.update_by_track_id

        # Загружаем известные лица из каталогов, если путь указан
        if data_path:
            self.load_known_faces_from_directories(data_path)
        else:
            print("No data path specified for known faces directories")

    def is_face_frontal(self, face_box, lm):
        """
        Checks if face is frontal using bounding box and 5 key points.

        Args:
          face_box: (x_face, y_face, x1_face, y1_face)
          lm: landmarks array size (5,2): [left eye, right eye, nose, left mouth corner, right mouth corner]

        Returns:
          True if face is suitable for recognition (adequate scale and orientation),
          otherwise False.
        """
        # Extract bounding box coordinates
        x_face, y_face, x1_face, y1_face = face_box
        face_width = x1_face - x_face
        face_height = y1_face - y_face
        scale = (face_width + face_height) / 2.0

        # Extract landmark points
        left_eye, right_eye = np.array(lm[0]), np.array(lm[1])
        nose = np.array(lm[2])
        mouth_left, mouth_right = np.array(lm[3]), np.array(lm[4])

        # Distances between key points
        eye_distance = np.linalg.norm(left_eye - right_eye)
        middle_eye = (left_eye + right_eye) / 2.0
        middle_mouth = (mouth_left + mouth_right) / 2.0
        face_vertical = np.linalg.norm(middle_mouth - middle_eye)

        # Calculate angles relative to horizontal
        def angle_between(p1, p2):
            return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

        eye_angle = angle_between(left_eye, right_eye)
        mouth_angle = angle_between(mouth_left, mouth_right)

        # Relative proportions, adapted by scale
        eye_ratio = eye_distance / scale
        vertical_ratio = face_vertical / scale

        # New criterion: ratio of distances from nose to middle point of eyes and to middle point of mouth
        nose_to_eyes = np.linalg.norm(nose - middle_eye)
        nose_to_mouth = np.linalg.norm(nose - middle_mouth)
        nose_ratio = nose_to_eyes / nose_to_mouth  # for a frontal face usually close to 1

        # Check tilt angles: if eyes or mouth are tilted more than 20°, face is probably not frontal
        if abs(eye_angle) > 20 or abs(mouth_angle) > 20:
            return False

        # Check proportions relative to scale
        if not (0.25 < eye_ratio < 0.55):
            return False
        if not (0.35 < vertical_ratio < 0.75):
            return False

        # Additional check: if face is tilted down, nose will be closer to mouth
        # For strictly frontal face nose_ratio should not be too small
        if nose_ratio < 0.8:
            return False

        return True

    def recognize_face(self, frame, face_location):
        """
        Recognize face and determine if it's a customer, waiter or celebrity.
        Try multiple times for unknown faces based on the recognition counter.
        """
        # Convert to format expected by face_recognition
        top, right, bottom, left = face_location
        face_location_tuple = (top, right, bottom, left)
        # Extract face encoding
        face_encoding = face_recognition.face_encodings(frame, [face_location_tuple])[0]

        # Check against known faces
        if len(self.known_faces['encodings']) > 0:
            matches = face_recognition.compare_faces(self.known_faces['encodings'], face_encoding)

            if True in matches:
                matched_idx = matches.index(True)
                name = self.known_faces['names'][matched_idx]
                person_type = self.known_faces['person_type'][matched_idx]
                return name, person_type

        return "unknown", PERSON_TYPE_CUSTOMER

    def analyze_face(self, frame, face_box, track_id):
        """
        Perform comprehensive face analysis: age, gender, emotion
        Only perform analysis if not already done for this track_id
        """
        # Check if we already have metadata for this track_id
        try:
            x_face, y_face, x1_face, y1_face = face_box

            # Ensure coordinates are within frame boundaries
            height, width = frame.shape[:2]
            x_face = max(0, x_face)
            y_face = max(0, y_face)
            x1_face = min(width, x1_face)
            y1_face = min(height, y1_face)

            # Skip if face region is too small
            if x1_face - x_face <= 10 or y1_face - y_face <= 10:
                print(f"Face region too small for track {track_id}: {face_box}")
                return None, None, None

            # Extract face region for analysis
            face_img = frame[y_face:y1_face, x_face:x1_face]

            # Ensure face image is not empty
            if face_img.size == 0 or face_img.shape[0] == 0 or face_img.shape[1] == 0:
                print(f"Empty face image for track {track_id}: {face_box}")
                return None, None, None

            face_img = Image.fromarray(face_img)

            # Estimate age
            age = age_estimator(face_img)

            # Estimate gender
            gender = gender_estimator(face_img)

            # Estimate emotion
            emotion = emotion_estimator(face_img)

            return age, gender, emotion
        except Exception as e:
            print(f"Error analyzing face for track {track_id}: {e}")
            return None, None, None

    def process_frame(self, frame):
        """
        Process a video frame for face detection, tracking, and analysis

        Args:
            frame: Video frame to process

        Returns:
            Modified frame if output=True, original frame if output=False
        """

        # Increment frame counter
        self.frame_count += 1

        # Get tracking information
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            log_warning("Frame is empty or invalid")
            return None

        detections = self.model.predict(frame, conf=0.5, verbose=False)
        if not detections:
            log_warning("No detections found")
            return None

        if isinstance(detections, list):
            detections = detections[0]

        boxes = detections.boxes
        bbox = boxes.xywh.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        class_id = boxes.cls.cpu().numpy().astype(int)

        if len(bbox) == 0:
            log_warning("No valid detections found")
            return None

        for i, box in enumerate(bbox):
            x1, y1, w1, h1 = box
            # bbox[i] = [x, y, x + w, y + h]
            # x1, y1, w1, h1 = map(int, [x1, y1, w1, h1])

            self.db_manager.write_detection_to_db(self.frame_count, coco_names[class_id[i]], class_id[i], x1, y1, x1 + w1, y1 + h1, round(conf[i], 2))

        trackers = self.tracker.update(bbox, conf, class_id, frame)
        # Detect faces and landmarks
        faces, landmarks = process_image(frame)

        for i, face in enumerate(faces):
            x_face, y_face, x1_face, y1_face = face[:4].astype(int)
            face_box = (x_face, y_face, x1_face, y1_face)

            # Match with tracker
            matched_id = None
            body_coordinates = None
            for track in trackers:
                x, y, x1, y1, obj_id, _, _ = map(int, track[:7])
                matched_id = obj_id
                if (x <= x_face <= x1 and y <= y_face <= y1) and (x <= x1_face <= x1 and y <= y1_face <= y1):
                    body_coordinates = (y, x1, y1, x)  # top, right, bottom, left (same format as face)
                    break

            # Skip if no matching tracker found
            if matched_id is None:
                # print('Skip ,no matching tracker found')
                continue

            # Check if face is visible and frontal
            visible = False
            if landmarks is not None and i < len(landmarks):
                lm = landmarks[i]
                visible = self.is_face_frontal(face[:4], lm)

            # Convert face location format for recognition
            face_location = (y_face, x1_face, y1_face, x_face)  # top, right, bottom, left

            # Initialize face data dictionary
            face_data = {
                "face_location": face_location
            }

            # Add body coordinates if available
            if body_coordinates:
                face_data["body_top"] = body_coordinates[0]
                face_data["body_right"] = body_coordinates[1]
                face_data["body_bottom"] = body_coordinates[2]
                face_data["body_left"] = body_coordinates[3]

            # Check if we already have metadata for this track_id in our memory cache
            track_meta = self.db_manager.get_frame_data(matched_id)
            if track_meta:
                # Update only the coordinate-related info and keep other metadata
                for key, value in track_meta.items():
                    if key not in ["face_location", "body_top", "body_right", "body_bottom", "body_left"]:
                        face_data[key] = value

                person_type = track_meta.get("person_type", PERSON_TYPE_CUSTOMER)

                if track_meta.get("name") == 'identifying..':
                    if visible:
                        recognition_result = self.recognize_face(frame, face_location)
                        if recognition_result:
                            name_new, person_type_new = recognition_result
                            if matched_id in self.track_metadata:
                                del self.track_metadata[matched_id]
                            self.db_manager.update_by_track_id(matched_id,
                                                               {"name": name_new, "person_type": person_type_new})
                        else:
                            if matched_id in self.track_metadata:
                                self.track_metadata[matched_id] += 1
                            else:
                                self.track_metadata[matched_id] = 1
                            if self.track_metadata[matched_id] == self.recognition_attempts:
                                self.db_manager.update_by_track_id(matched_id, {"name": "unknown"})

            else:
                # No cached data, process face if visible
                if visible:
                    # Try to recognize face
                    recognition_result = self.recognize_face(frame, face_location)

                    # If None is returned, skip this face for now (need more attempts)
                    if recognition_result[0] is None:
                        # Save minimal data and continue
                        face_data["name"] = "identifying..."
                        self.db_manager.save_frame_data(self.frame_count, matched_id, face_data, visible,
                                                        PERSON_TYPE_CUSTOMER)
                        continue

                    name, person_type = recognition_result
                    face_data["name"] = name
                    face_data["person_type"] = person_type

                    # Analyze face (age, gender, emotion) only if not already done
                    age, gender, emotion = self.analyze_face(frame, face_box, matched_id)

                    if age:
                        face_data["age"] = age
                    if gender:
                        face_data["gender"] = gender
                    if emotion:
                        face_data["emotion"] = emotion

                    # Save to appropriate tables based on person_type
                    self.db_manager.save_face_data(self.frame_count, matched_id, face_data)
                else:
                    face_data["name"] = "identifying..."
                    person_type = PERSON_TYPE_CUSTOMER

            # Always save frame data for each frame
            self.db_manager.save_frame_data(self.frame_count, matched_id, face_data, visible, person_type)

    def load_known_faces_from_directories(self, base_path):
        """
        Загружает известные лица из структурированных каталогов.

        Ожидаемая структура:
        base_path/
            celebrities/
                person_name1/
                    image1.jpg
                    image2.jpg
                person_name2/
                    ...
            waiters/
                person_name1/
                    ...
            customers/
                person_name1/
                    ...
        """
        person_types = {
            'celebrities': PERSON_TYPE_CELEBRITY,
            'waiters': PERSON_TYPE_WAITER,
            'customers': PERSON_TYPE_CUSTOMER
        }

        for category, person_type in person_types.items():
            category_path = os.path.join(base_path, category)

            if not os.path.exists(category_path):
                print(f"Warning: Directory {category_path} does not exist")
                continue

            # Обходим каталоги с именами людей
            for person_name in os.listdir(category_path):
                person_dir = os.path.join(category_path, person_name)

                if not os.path.isdir(person_dir):
                    continue

                print(f"Processing {person_type}: {person_name}")

                # Обходим изображения лиц
                for image_file in os.listdir(person_dir):
                    # Проверяем, что это изображение
                    if not image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        continue

                    image_path = os.path.join(person_dir, image_file)
                    try:
                        # Загружаем изображение
                        image = face_recognition.load_image_file(image_path)

                        # Регистрируем лицо в базе
                        result, message = self.register_new_face(image, person_name, person_type)

                        if result:
                            print(f"  + {image_file}: {message}")
                        else:
                            print(f"  - {image_file}: {message}")
                    except Exception as e:
                        print(f"  Error processing {image_path}: {e}")

    def register_new_face(self, frame, name, person_type=PERSON_TYPE_CUSTOMER):
        """
        Register a new face to the known faces database
        """
        # Detect faces in frame
        face_locations = face_recognition.face_locations(frame)

        if len(face_locations) == 0:
            return False, "No face detected"

        if len(face_locations) > 1:
            return False, "Multiple faces detected, please ensure only one face is in frame"

        # Extract face encoding
        face_encoding = face_recognition.face_encodings(frame, face_locations)[0]

        # Save to database
        self.db_manager.register_known_face(name, face_encoding, person_type)

        # Update local cache
        self.known_faces['encodings'].append(face_encoding)
        self.known_faces['names'].append(name)
        self.known_faces['person_type'].append(person_type)

        return True, f"Successfully registered {name} as {person_type}"


# Example usage
if __name__ == "__main__":
    # Initialize database connection
    db_manager = DatabaseManager(
        dbname="mvp_db",
        user="mvp",
        password="123",
        host="localhost",
        port=5432
    )

    # Путь к директории с известными лицами
    data_path = "face/model/face_id/data_face/"

    # Initialize face processor with 3 recognition attempts
    face_processor = FaceProcessor(db_manager, recognition_attempts=3, data_path=data_path)

    print("Processing video...")

    saved_frames = db_manager.get_unprocessed_frames()
    for saved_frame in saved_frames:
        frame = cv2.imread(saved_frame['frame_path'])
        ret = frame is not None

        if not ret:
            break

        # Обрабатываем кадр
        face_processor.process_frame(frame)

        # Отмечаем обработанные кадры
        db_manager.mark_frame_as_processed(saved_frame['id'])


        # Проверяем нажатие клавиши для выхода
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break