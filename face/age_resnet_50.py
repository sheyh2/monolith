import os
import sys
import torch
from torchvision import transforms
from PIL import Image
from face.model.model_resnet50 import AgeEstimationBNN
import time




class AgeEstimator:
    def __init__(self):
        """
        Инициализация: установка устройства, загрузка модели и определение трансформаций.
        """
        # Если устройство не передано, выбираем cuda при наличии GPU или cpu
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        checkpoint_path = r'face/checkpoint/resnet_50.pt'
        self.model = self.load_model(checkpoint_path)
        # Определяем цепочку трансформаций
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

    def load_model(self, checkpoint_path):
        """
        Загружает модель и чекпоинт.
        """
        model = AgeEstimationBNN().to(self.device)

        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Файл чекпоинта не найден: {checkpoint_path}")

        try:
            checkpoint = torch.load(checkpoint_path, map_location=self.device)
        except Exception as e:
            raise RuntimeError(f"Ошибка при загрузке чекпоинта: {e}")

        # Если чекпоинт содержит ключ 'state_dict', используем его
        state_dict = checkpoint['state_dict'] if 'state_dict' in checkpoint else checkpoint
        model.load_state_dict(state_dict)


        model.eval()
        return model

    def __call__(self, images):
        """
        Обрабатывает одиночное изображение: применяет трансформации и проводит через модель.
        """
        if not isinstance(images, list):
            images = [images]
        image_tensor = [self.transform(img) for img in images]
        image_tensor = torch.stack(image_tensor, dim=0).to(self.device)
        # Если изображение не имеет размерности батча, добавляем её
        if image_tensor.dim() == 3:
            image_tensor = image_tensor.unsqueeze(0)
        elif image_tensor.dim() != 4:
            raise ValueError("Преобразованное изображение имеет некорректное число размерностей")

        image_tensor = image_tensor.to(self.device)

        with torch.no_grad():
            output = self.model(image_tensor)
        return str(int(output[0]))



if __name__ == '__main__':

    dummy_image = Image.new('RGB', (224, 224))
    batch_images = [dummy_image] * 32


    estimator = AgeEstimator()

    start_time = time.time()

    output = estimator(batch_images)

    elapsed_time = time.time() - start_time
    print(f"Время обработки батча из 32 изображений: {elapsed_time:.4f} секунд")
