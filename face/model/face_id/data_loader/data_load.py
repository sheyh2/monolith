import os

def load_data(path):
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
    return person_image_paths,person_names