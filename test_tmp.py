import cv2
import requests
import numpy as np

# Указываем URL API
API_URL = 'http://127.0.0.1:8000/upload-frame'


# Функция для отправки кадра на API
def send_frame_to_api(frame):
    # Преобразуем кадр в байты (JPEG)
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_bytes = img_encoded.tobytes()

    # Отправляем кадр через POST-запрос
    files = {'file': ('frame.jpg', img_bytes, 'image/jpeg')}
    response = requests.post(API_URL, files=files)

    if response.status_code == 200:
        print("Кадр успешно отправлен!")
    else:
        print(f"Ошибка при отправке кадра: {response.status_code}")


# Открываем видео
video_path = 'data/test.mp4'
cap = cv2.VideoCapture(video_path)

# Проверяем, открылся ли видеофайл
if not cap.isOpened():
    print("Ошибка при открытии видеофайла")
    exit()

frame_rate = cap.get(cv2.CAP_PROP_FPS)  # Получаем частоту кадров видео

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Отправляем кадр на API
    send_frame_to_api(frame)

    # Пауза, чтобы не перегрузить сервер, можно настроить задержку (по умолчанию равна времени одного кадра)
    cv2.waitKey(int(1000 / frame_rate))

# Закрываем видео
cap.release()
cv2.destroyAllWindows()
