import face_recognition
import cv2
import os


class FaceRecognizer:
    def __init__(self):
        data_path = r'face/model/face_id/data_face'
        # Загрузка данных (пути к изображениям и имена)
        self.person_image_paths, self.person_names = self.load_data(data_path)
        # Вычисляем известные энкодинги лиц и соответствующие имена
        self.known_face_encodings, self.known_names = self.load_known_faces(self.person_image_paths, self.person_names)

    def load_data(self, path):
        person_image_paths = []
        person_names = []
        labels = os.listdir(path)
        for label in labels:
            label_path = os.path.join(path, label)
            img2_path = os.listdir(label_path)
            for i in img2_path:
                img_path = os.path.join(label_path, i)
                person_image_paths.append(img_path)
                person_names.append(label)
        return person_image_paths, person_names

    def load_known_faces(self, image_paths, names):
        known_face_encodings = []
        known_names = []
        for image_path, name in zip(image_paths, names):
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            known_face_encodings.extend(face_encodings)
            known_names.extend([name] * len(face_encodings))
        return known_face_encodings, known_names
    def recognize_face_img(self, frame, face_locations):
        data = {}
        for face_location in face_locations:
            name = "Unknown"
            # top, right, bottom, left = face_location
            # Получаем энкодинг найденного лица
            face_encoding = face_recognition.face_encodings(frame, [face_location])[0]
            # Сравниваем с известными энкодингами лиц
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.3)
            if True in matches:
                first_match_index = matches.index(True)
                name = self.known_names[first_match_index]
            data[face_location]=name
        return data
if __name__ == "__main__":
    face_id = FaceRecognizer()

    path_img = '/media/gis_lab/9AF47E94F47E71FD1/restaurant_manalit/face/images/faces.jpg'
    frame = cv2.imread(path_img)
    face_locations = face_recognition.face_locations(frame)
    data = face_id.recognize_face_img(frame, face_locations)
    print(data)
