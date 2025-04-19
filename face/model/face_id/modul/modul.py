import face_recognition
import cv2
import os
import time
import tkinter as tk
from deepface import DeepFace

from tkinter import ttk
import tkinter as tk
from tkinter import scrolledtext

def display_dict(dictionary):
    out = ['dominant_emotion', 'dominant_gender', 'dominant_race', 'age', 'name']

    # Создание главного окна
    root = tk.Tk()
    root.title("Информация о лице")

    # Создание таблицы
    tree = ttk.Treeview(root, columns=out, show='headings', height=5)
    tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Определение заголовков колонок
    for col in out:
        tree.heading(col, text=col)
        tree.column(col, width=100)

    # Вставка данных в таблицу
    data = [(dictionary[key] if key in dictionary else "N/A") for key in out]
    tree.insert('', 'end', values=data)

    # Запуск главного цикла обработки событий
    root.mainloop()



def load_known_faces(image_paths, names):
    known_face_encodings = []
    known_names = []
    for image_path, name in zip(image_paths, names):
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        known_face_encodings.extend(face_encodings)
        known_names.extend([name] * len(face_encodings))
    return known_face_encodings, known_names

def recognize_faces(video_capture, known_face_encodings, known_names):
    while True:
        start_time = time.time()
        ret, frame = video_capture.read()
        if not ret:
            break
        face_locations = face_recognition.face_locations(frame)
        for face_location in face_locations:
            top, right, bottom, left = face_location
            face_encoding = face_recognition.face_encodings(frame, [face_location])[0]
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"
            if True in matches:
                first_match_index = matches.index(True)
                name = known_names[first_match_index]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
        cv2.imshow('Video', frame)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time} seconds")
        if cv2.waitKey(1) == 13:
            result = DeepFace.analyze(frame,['emotion','gender','race','age'])
            a = result[0]
            a['name'] = name
            display_dict(a)
            break
    video_capture.release()
    cv2.destroyAllWindows()

def recognize_face_img(path, known_face_encodings, known_names):
    frame = cv2.imread(path)
    face_locations = face_recognition.face_locations(frame)
    for face_location in face_locations:
        top, right, bottom, left = face_location
        face_encoding = face_recognition.face_encodings(frame, [face_location])[0]
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
        name = "Unknown"
        if True in matches:
            first_match_index = matches.index(True)
            name = known_names[first_match_index]
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
    cv2.imshow('Video', frame)
    if cv2.waitKey(0) == 13:
        result = DeepFace.analyze(frame, ['emotion', 'gender', 'race', 'age'], enforce_detection=False)
        a = result[0]
        a['name'] = name
        display_dict(a)
