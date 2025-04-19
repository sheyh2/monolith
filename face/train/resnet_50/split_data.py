import random


def split_txt_file(txt_file, train_file, test_file, train_ratio=0.8):
    """
    Разделяет .txt файл на тренировочный и тестовый набор.

    Args:
        txt_file (str): Путь к исходному .txt файлу.
        train_file (str): Путь для сохранения тренировочного набора.
        test_file (str): Путь для сохранения тестового набора.
        train_ratio (float): Доля данных для обучения (по умолчанию 0.8).
    """
    with open(txt_file, 'r') as file:
        lines = file.readlines()

    # Перемешиваем строки
    random.shuffle(lines)

    # Считаем индекс для разделения
    split_index = int(len(lines) * train_ratio)

    # Разделяем строки
    train_lines = lines[:split_index]
    test_lines = lines[split_index:]

    # Сохраняем в отдельные файлы
    with open(train_file, 'w') as train_f:
        train_f.writelines(train_lines)

    with open(test_file, 'w') as test_f:
        test_f.writelines(test_lines)


# Пример использования:
if __name__ == "__main__":
    input_txt = r"/media/gis_lab/9AF47E94F47E71FD/ulugbek/data/metadata/B3FD_metadata/B3FD_age.csv"  # Исходный файл
    train_txt = "train.txt"  # Файл для обучения
    test_txt = "test.txt"  # Файл для тестирования

    split_txt_file(input_txt, train_txt, test_txt, train_ratio=0.8)