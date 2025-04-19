from face.age_resnet_50 import AgeEstimator


from face.face_pointing import process_image
from face.face_recog import FaceRecognizer

from face.gender_detection import GenderEstimator

from face.res_emote_net_emotion import EmotionEstimator

import face_recognition
from tracking.tracking_person import ObjectTracking
import torch
import cv2
import numpy as np
import math
import sqlite3
from datetime import datetime


class Counting:
    """
    Class for object detection, tracking, and visualization.
    """

    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print("Using Device: ", self.device)
        self.tracker = ObjectTracking()
        self.face_id = FaceRecognizer()

    def is_face_frontal(self, face_box, lm):
        """
        Проверяет, смотрит ли лицо строго вперёд, используя bounding box и 5 ключевых точек.

        Аргументы:
          face_box: (x_face, y_face, x1_face, y1_face)
          lm: массив landmarks размером (5,2): [левый глаз, правый глаз, нос, левый угол рта, правый угол рта]

        Возвращает:
          True, если лицо подходит для распознавания (адекватный масштаб и ориентация),
          иначе False.
        """
        # Извлекаем координаты bounding box
        x_face, y_face, x1_face, y1_face = face_box
        face_width = x1_face - x_face
        face_height = y1_face - y_face
        scale = (face_width + face_height) / 2.0

        # Из landmarks извлекаем точки
        left_eye, right_eye = np.array(lm[0]), np.array(lm[1])
        nose = np.array(lm[2])
        mouth_left, mouth_right = np.array(lm[3]), np.array(lm[4])

        # Расстояния между ключевыми точками
        eye_distance = np.linalg.norm(left_eye - right_eye)
        middle_eye = (left_eye + right_eye) / 2.0
        middle_mouth = (mouth_left + mouth_right) / 2.0
        face_vertical = np.linalg.norm(middle_mouth - middle_eye)

        # Вычисляем углы относительно горизонтали
        def angle_between(p1, p2):
            return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

        eye_angle = angle_between(left_eye, right_eye)
        mouth_angle = angle_between(mouth_left, mouth_right)

        # Относительные соотношения, адаптированные по масштабу
        eye_ratio = eye_distance / scale
        vertical_ratio = face_vertical / scale

        # Новый критерий: соотношение расстояний от носа до средней точки глаз и до средней точки рта.
        nose_to_eyes = np.linalg.norm(nose - middle_eye)
        nose_to_mouth = np.linalg.norm(nose - middle_mouth)
        nose_ratio = nose_to_eyes / nose_to_mouth  # для фронтального лица обычно близко к 1

        # Отладочная информация (при необходимости можно раскомментировать)
        # print("scale:", scale, "eye_distance:", eye_distance, "face_vertical:", face_vertical)
        # print("eye_ratio:", eye_ratio, "vertical_ratio:", vertical_ratio)
        # print("eye_angle:", eye_angle, "mouth_angle:", mouth_angle, "nose_ratio:", nose_ratio)

        # Проверка углов наклона: если глаза или рот наклонены более чем на 10°, лицо, скорее всего, не фронтальное
        if abs(eye_angle) > 20 or abs(mouth_angle) > 20:
            return False

        # Проверка соотношений относительно масштаба
        if not (0.25 < eye_ratio < 0.55):
            return False
        if not (0.35 < vertical_ratio < 0.75):
            return False

        # Дополнительная проверка: если лицо наклонено вниз, нос окажется ближе к рту.
        # Для строго фронтального лица nose_ratio должно быть не слишком маленьким.
        if nose_ratio < 0.8:
            return False

        return True


    def __call__(self, frame):
        trackers = self.tracker(frame)
        faces, landmarks = process_image(frame)
        out = []

        for i, face in enumerate(faces):
            x_face, y_face, x1_face, y1_face = face[:4].astype(int)
            face_box = (x_face, y_face, x1_face, y1_face)

            matched_id = None
            for track in trackers:
                x, y, x1, y1 = map(int, track.tlbr)
                if (x <= x_face <= x1 and y <= y_face <= y1) and (x <= x1_face <= x1 and y <= y1_face <= y1):
                    matched_id = track.track_id
                    break

            visible = False
            if landmarks is not None:
                lm = landmarks[i]
                visible = self.is_face_frontal(face[:4], lm)

            if matched_id is not None:
                color = (0, 255, 0) if visible else (0, 0, 255)
                cv2.rectangle(frame, (x_face, y_face), (x1_face, y1_face), color, 2)
                cv2.putText(frame, f"ID: {matched_id} {'OK' if visible else 'BAD'}",
                            (x_face, y_face - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                # === RECOGNITION + DATABASE ===
                if visible:
                    # Подготавливаем "face_location" для face_recognition
                    face_location = [(y_face, x1_face, y1_face, x_face)]  # top, right, bottom, left
                    data = self.face_id.recognize_face_img(frame, face_location)
                    if data:
                        name = data[0]['name']  # Предположим, это так
                    else:
                        name = 'unknown'

                    # self.save_to_db(matched_id, name, y_face, x1_face, y1_face, x_face)
                    out.append((matched_id, name, y_face, x1_face, y1_face, x_face))
        return out
    # def __call__(self, frame):
    #     trackers = self.tracker(frame)
    #     faces, landmarks = process_image(frame)
    #     face_ids = []
    #
    #     for i, face in enumerate(faces):
    #         # print(f"face shape: {face.shape}, values: {face}")
    #
    #         x_face, y_face, x1_face, y1_face = face[:4].astype(int)
    #         face_box = (x_face, y_face, x1_face, y1_face)
    #
    #         # Поиск трека, в который входит лицо
    #         matched_id = None
    #         for track in trackers:
    #             x, y, x1, y1 = map(int, track.tlbr)
    #             track_box = (x, y, x1, y1)
    #
    #             # Проверка: входит ли face_box внутрь track_box
    #             if (x <= x_face <= x1 and y <= y_face <= y1) and (x <= x1_face <= x1 and y <= y1_face <= y1):
    #                 matched_id = track.track_id
    #                 break
    #
    #         # Оценка видимости по landmarks
    #         visible = False
    #         if landmarks is not None:
    #             lm = landmarks[i]
    #             visible = self.is_face_frontal(face[:4], lm)
    #
    #         # Подписи и отрисовка
    #         if matched_id is not None:
    #             color = (0, 255, 0) if visible else (0, 0, 255)
    #             cv2.rectangle(frame, (x_face, y_face), (x1_face, y1_face), color, 2)
    #             cv2.putText(frame, f"ID: {matched_id} {'OK' if visible else 'BAD'}",
    #                         (x_face, y_face - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    #
    #     return frame


