from face.model.ResEmoteNet.approach.ResEmoteNet import ResEmoteNet
from PIL import Image
import torch
from torchvision import transforms
import time
# Set the device





class EmotionEstimator:
    def __init__(self):
        """
        Инициализация: установка устройства, загрузка модели и определение трансформаций.
        """
        # Если устройство не передано, выбираем cuda при наличии GPU или cpu
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.Grayscale(num_output_channels=3),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        checkpoint_path = r'face/checkpoint/res_emoteNet.pth'
        self.model = self.load_model(checkpoint_path)
        self.emotions = ['happy', 'surprise', 'sad', 'anger', 'disgust', 'fear', 'neutral']
    def load_model(self, checkpoint_path):
        """
        Загружает модель и чекпоинт.
        """
        model = ResEmoteNet().to(self.device)
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(self.device)
        model.eval()
        return model
    def __call__(self, image):
        """
        Позволяет вызывать экземпляр класса как функцию.
        Поддерживает одиночное изображение или список изображений.
        """
        image_tensors = self.transform(image).to(self.device)
        # image_tensors = torch.stack(image_tensors, dim=0).to(self.device)
        if image_tensors.dim() == 3:
            image_tensors = image_tensors.unsqueeze(0)
        else:
            raise ValueError("Преобразованное изображение имеет некорректное число размерностей")

        with torch.no_grad():
            output = self.model(image_tensors)
        _, predicted = torch.max(output.data, 1)
        pre = self.emotions[predicted]
        return pre

import numpy as np
if __name__ == "__main__":
    checkpoint_path = r'checkpoint/res_emoteNet.pth'

    estimator = EmotionEstimator()

    # Генерация fake dataset (32 изображения размера 3x64x64)
    dummy_image = Image.new('RGB', (64, 64))
    batch_images = [dummy_image] * 32

    start_time = time.time()
    predictions = estimator(batch_images)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Inference time for batch size {32}: {elapsed_time:.4f} seconds")
    print(f"Predicted emotion classes: {predictions.cpu().numpy()}")