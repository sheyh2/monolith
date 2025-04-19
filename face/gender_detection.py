import numpy as np
import onnxruntime as ort
from PIL import Image
import torch
from torchvision import transforms
import time
# Set the device




class GenderEstimator:
    def __init__(self):
        """
        Инициализация: установка устройства, загрузка модели и определение трансформаций.
        """
        # Если устройство не передано, выбираем cuda при наличии GPU или cpu
        sess_options = ort.SessionOptions()
        sess_options.log_severity_level = 3  # Показывать только ошибки
        self.session = ort.InferenceSession(r"face/checkpoint/vit_gender.onnx", sess_options=sess_options,
                                       providers=['CUDAExecutionProvider'])
        # self.session = ort.InferenceSession(r"checkpoint\vit_gender.onnx", providers=['CUDAExecutionProvider'])

        # Получаем имя первого входного узла модели
        self.input_name = self.session.get_inputs()[0].name
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),     # нужный размер для вашей модели
            transforms.ToTensor(),             # (C, H, W), float32, 0–1
        ])
    def __call__(self, image):
        """
        Позволяет вызывать экземпляр класса как функцию.
        Поддерживает одиночное изображение или список изображений.
        """
        # if image_tensors.dim() == 3:
        #     image_tensors = image_tensors.unsqueeze(0)
        # elif image_tensors.dim() != 4:
        #     raise ValueError("Преобразованное изображение имеет некорректное число размерностей")
         # Преобразует в тензор с dtype=float32, нормализует от 0 до 1
        image_tensor = self.transform(image).unsqueeze(0)
        image_np = image_tensor.numpy().astype(np.float32)
        with torch.no_grad():
            outputs = self.session.run(None, {self.input_name: image_np})
        max_index = np.argmax(outputs)
        print(max_index)
        if max_index == 0:
            return 'MAN'
        else:
            return "WOMAN"

import numpy as np
if __name__ == "__main__":
    estimator = GenderEstimator()
    # Создаем тензор с помощью PyTorch непосредственно на GPU
    tensor_input = torch.randn(32, 3, 224, 224)

    # Переносим тензор на CPU и преобразуем в numpy-массив (onnxruntime принимает numpy-массивы)
    input_data = tensor_input.cpu().numpy().astype(np.float32)

    start_time = time.time()
    predictions = estimator(input_data)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Inference time for batch size {32}: {elapsed_time:.4f} seconds")
