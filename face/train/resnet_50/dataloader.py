import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
import random
class TxtDataset(Dataset):
    def __init__(self, txt_file, path_image, transform=None):
        """
        Args:
            txt_file (str): Путь к .txt файлу.
            transform (callable, optional): Трансформации для изображений.
        """
        self.data = []
        self.transform = transform
        with open(txt_file, 'r') as file:
            for line in file:
                path, age = line.strip().rsplit(' ', 1)
                path = os.path.join(path_image, path)
                self.data.append((path, int(age)))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_path, age = self.data[idx]
        # print(img_path)
        # Загрузка изображения
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, age
    
class Dataset_folder(Dataset):
    def __init__(self, path_image, transform=None):
        """
        Args:
            txt_file (str): Путь к .txt файлу.
            transform (callable, optional): Трансформации для изображений.
        """
        self.data = []
        self.transform = transform
        file = os.listdir(path_image)
        for label in file:
            path_label = os.path.join(path_image, label)
            for img in os.listdir(path_label):
                path_img = os.path.join(path_label, img)
                self.data.append((path_img, int(label)))

    def __len__(self):
        return len(self.data)

    # def __getitem__(self, idx):
    #     img_path, age = self.data[idx]
    #     # Загрузка изображения
    #     image = Image.open(img_path).convert("RGB")
    #     if self.transform:
    #         image = self.transform(image)
    #     return image, age

    def __getitem__(self, index):
        img_path = self.img_paths[index]
        try:
            img = Image.open(img_path).convert("RGB")
        except (OSError, IOError):
            print(f"Error loading  {img_path}")
            img = Image.new("RGB", (224, 224), (0, 0, 0))  # Заглушка

        if self.transform:
            img = self.transform(img)

        return img


