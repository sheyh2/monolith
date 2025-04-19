import numpy as np
from face.model.retinaface.retinaface import RetinaFace
import os
# Инициализация детектора один раз, на GPU (gpuid=0)
GPUID = 0
MODEL_PATH = 'face/checkpoint/R50/R50'
# MODEL_PATH = 'checkpoint/R50'
path = os.path.join(os.getcwd(),MODEL_PATH)
DETECTOR = RetinaFace(path,0, -1, 'net3')

def process_image(img, thresh=0.8, do_flip=False, image_out=False):
    """
    Обрабатывает изображение:
      - вычисляет коэффициент масштабирования,
      - детектирует лица с использованием GPU,
      - (при необходимости) отрисовывает найденные прямоугольники и точки (landmarks).
    """
    im_shape = img.shape
    target_size, max_size = 1024, 1980
    im_size_min = np.min(im_shape[0:2])
    im_size_max = np.max(im_shape[0:2])
    im_scale = float(target_size) / float(im_size_min)
    if np.round(im_scale * im_size_max) > max_size:
        im_scale = float(max_size) / float(im_size_max)
    scales_list = [im_scale]

    # Детектирование лиц с использованием заранее инициализированного DETECTOR (на GPU)
    faces, landmarks = DETECTOR.detect(img, thresh, scales=[1.0], do_flip=do_flip)
    if image_out:
        for i in range(faces.shape[0]):
            # Приведение координат к целым числам
            box = faces[i].astype(np.int32)
            color = (0, 0, 255)  # Красный прямоугольник
            cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), color, 2)
            if landmarks is not None:
                landmark5 = landmarks[i].astype(np.int32)
                for l in range(landmark5.shape[0]):
                    # Отмечаем глаза зелёным, остальные красным
                    point_color = (0, 255, 0) if l in [0, 3] else (0, 0, 255)
                    cv2.circle(img, (landmark5[l][0], landmark5[l][1]), 1, point_color, 2)
        return img, faces, landmarks
    return faces, landmarks
import cv2
import time


def main():
    # Если вы хотите использовать видеофайл, замените 0 на путь к файлу, например:
    cap = cv2.VideoCapture('/media/ulugbek/Новый том2/res/data/test.mp4')
    # cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Не удалось открыть поток видео")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Не удалось получить кадр из видео или достигнут конец видео")
            break
        start_time = time.time()
        # Предполагается, что функция process_image определена для обработки кадра
        processed_frame, faces, landmarks = process_image(frame, image_out=True)
        end_time = time.time()
        total_time = end_time - start_time
        print(f"Обработка кадра заняла {total_time:.2f} секунд")
        cv2.imshow("Processed Frame", processed_frame)
        # Выход из цикла по нажатию клавиши 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
